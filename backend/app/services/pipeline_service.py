"""End-to-end case processing orchestrator (FRS §9).

Wires the individual services into the pipeline described in FRS §4.3::

    1. load case + photos
    2. ensure each photo has a 512-d ArcFace embedding (detect → embed)
    3. compute aging trajectory Δv across photo ages
    4. age the most-recent photo to case.predicted_current_age
    5. detect + embed the aged photo → e_target
    6. find nearest sightings by cosine similarity
    7. score each candidate and route (auto-alert / review / inconclusive)
    8. generate case summary via LLM (optional, GPT4O_ENABLED)
    9. write a final audit entry with runtime + providers used

The ``providers_used`` field in the return value is what judges read to know
which free-tier provider actually served each sub-step. In mock mode all
sub-steps report ``mock`` / ``template``.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, TypedDict

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Case, Photo
from app.services import (
    aging_service,
    alert_router,
    audit_service,
    embedding_service,
    face_detector,
    llm_service,
    recognition_service,
    scoring_service,
    trajectory_service,
)
from app.services.ai_common import InsufficientPhotosError

logger = logging.getLogger(__name__)


class ProvidersUsed(TypedDict):
    aging: str
    llm: str


class PipelineResult(TypedDict):
    case_id: str
    aged_photo_url: str
    matches: list[dict]
    summary: str | None
    processing_time_seconds: float
    providers_used: ProvidersUsed


def _fetch_bytes(url: str) -> bytes:
    """Fetch image bytes; in mock mode we return empty bytes since mocks are seeded from URL strings."""
    if get_settings().use_mock_ai:
        return b""
    resp = httpx.get(url, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def _ensure_embedding(photo: Photo) -> list[float]:
    if photo.embedding:
        return list(photo.embedding)
    detection = face_detector.detect_face(_fetch_bytes(photo.supabase_url) or photo.supabase_url)
    vec = embedding_service.get_embedding(detection["face_img_bytes"])
    photo.embedding = vec.tolist()
    return photo.embedding


def process_case(
    session: Session,
    case_id: str,
    *,
    actor_id: uuid.UUID | None = None,
) -> PipelineResult:
    started = time.monotonic()

    case = session.get(Case, case_id)
    if case is None:
        raise ValueError(f"case {case_id} not found")

    source_photos = [p for p in case.photos if not p.is_predicted_aged]
    if len(source_photos) < trajectory_service.MIN_PHOTOS:
        raise InsufficientPhotosError(
            f"case {case_id} has {len(source_photos)} source photos; need at least "
            f"{trajectory_service.MIN_PHOTOS} (FRS FR-2.3)."
        )

    # 2. detect + embed each photo (cache on Photo.embedding)
    for photo in source_photos:
        _ensure_embedding(photo)
    session.flush()

    # 3. trajectory
    trajectory_service.compute_trajectory(
        [{"embedding": p.embedding, "age_at_photo": p.age_at_photo} for p in source_photos]
    )

    # 4. age the most-recent photo to the predicted-current age
    reference = max(source_photos, key=lambda p: p.age_at_photo)
    target_age = case.predicted_current_age
    source_bytes = _fetch_bytes(reference.supabase_url)
    aging_result = aging_service.age_progress(source_bytes, target_age, case.case_id)

    # 5. record the aged photo
    aged_photo = Photo(
        case_id=case.case_id,
        supabase_url=aging_result["url"],
        age_at_photo=target_age,
        is_predicted_aged=True,
    )
    session.add(aged_photo)
    session.flush()

    # detect + embed aged photo (in mock mode, pass the URL string as seed)
    aged_source: Any = _fetch_bytes(aging_result["url"]) or aging_result["url"]
    aged_detection = face_detector.detect_face(aged_source)
    aged_embedding = embedding_service.get_embedding(aged_detection["face_img_bytes"])
    aged_photo.embedding = aged_embedding.tolist()
    session.flush()

    # 6. find matches (exclude the case's own photos)
    candidates = recognition_service.find_matches(
        session, aged_embedding, top_k=10, exclude_case_id=case.case_id
    )

    # 7. score + route each candidate
    match_records: list[dict] = []
    for cand in candidates:
        score = scoring_service.compute_confidence(session, cand["similarity_score"])
        routed = alert_router.route(
            session,
            case,
            candidate_photo_id=cand["photo_id"],
            similarity_score=score["score"],
            tier=score["tier"],
            actor_id=actor_id,
        )
        match_records.append(
            {
                "candidate_case_id": cand["case_id"],
                "candidate_photo_id": cand["photo_id"],
                "photo_url": cand["photo_url"],
                "similarity_score": cand["similarity_score"],
                "confidence": score["score"],
                "tier": score["tier"],
                "action": score["action"],
                "match_id": routed["match_id"],
                "assigned_field_worker_id": routed["assigned_field_worker_id"],
                "cluster_alert": routed["cluster_alert"],
            }
        )

    # 8. optional LLM case summary
    summary_text: str | None = None
    llm_provider = "disabled"
    if get_settings().gpt4o_enabled or get_settings().use_mock_ai:
        llm_out = llm_service.generate_case_summary(
            {
                "case_id": case.case_id,
                "person_name": case.person_name,
                "year_missing": case.year_missing,
                "age_at_disappearance": case.age_at_disappearance,
                "last_seen_location": case.last_seen_location,
                "identifying_marks": case.identifying_marks,
            },
            session=session,
            actor_id=actor_id,
        )
        summary_text = llm_out["text"]
        llm_provider = llm_out["provider"]

    elapsed = time.monotonic() - started

    # 9. audit the whole pipeline invocation
    audit_service.write_audit(
        session,
        action="pipeline.process_case",
        actor_id=actor_id,
        model_version=aging_result["model_version"],
        prompt_version=None,
        input_data={"case_id": case.case_id, "target_age": target_age},
        output_data={
            "aged_photo_url": aging_result["url"],
            "aging_provider": aging_result["provider"],
            "match_count": len(match_records),
            "processing_time_seconds": elapsed,
        },
        confidence_score=max((m["confidence"] for m in match_records), default=None),
    )

    session.commit()

    return PipelineResult(
        case_id=case.case_id,
        aged_photo_url=aging_result["url"],
        matches=match_records,
        summary=summary_text,
        processing_time_seconds=elapsed,
        providers_used=ProvidersUsed(aging=aging_result["provider"], llm=llm_provider),
    )
