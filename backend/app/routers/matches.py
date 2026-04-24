"""/matches — field-worker verification workflow (FRS §6.5, FR-5.1–FR-5.5).

Thin HTTP wrapper over services:
* ``llm_service.generate_family_alert`` for Confirm Match notifications.
* ``not_match_service`` (below) handles the error-vector + fine-tune trigger.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_db, require_role
from app.models import (
    Case,
    CaseStatus,
    Match,
    MatchStatus,
    NotMatchFeedback,
    Photo,
    User,
    UserRole,
)
from app.schemas.match import ConfirmMatchResponse, NotMatchResponse, PendingMatch
from app.services import audit_service, llm_service, supabase_service

logger = logging.getLogger(__name__)

router = APIRouter()

FINE_TUNE_TRIGGER_COUNT = 50  # FRS FR-5.5


def _explanation(tier: str, score: float) -> str:
    return (
        f"Confidence is {score:.0%} ({tier}). "
        "This is an estimate produced by Artificial Intelligence (AI). "
        "Please have the result verified by a certified officer before acting upon it."
    )


@router.get("/pending", response_model=list[PendingMatch])
def list_pending(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FIELD_WORKER)),
) -> list[PendingMatch]:
    stmt = (
        select(Match)
        .where(Match.field_worker_id == user.id, Match.status == MatchStatus.PENDING)
        .order_by(Match.confidence_score.desc())
    )
    rows = db.execute(stmt).scalars().all()
    return [
        PendingMatch(
            id=str(m.id),
            case_id=m.case_id,
            person_name=m.case.person_name,
            candidate_photo_url=m.candidate_photo.supabase_url if m.candidate_photo else "",
            confidence_score=m.confidence_score,
            tier=m.tier,
            created_at=m.created_at,
            explanation=_explanation(m.tier, m.confidence_score),
        )
        for m in rows
    ]


def _load_match_for_worker(db: Session, match_id: str, worker: User) -> Match:
    try:
        import uuid as _u

        match_uuid = _u.UUID(match_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="match_id must be a UUID.") from exc
    match = db.get(Match, match_uuid)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found.")
    if match.field_worker_id != worker.id and worker.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="This match is not assigned to you.")
    return match


@router.post("/{match_id}/confirm", response_model=ConfirmMatchResponse)
def confirm_match(
    match_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FIELD_WORKER, UserRole.ADMIN)),
) -> ConfirmMatchResponse:
    match = _load_match_for_worker(db, match_id, user)
    if match.status != MatchStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Match is already {match.status}.")

    match.status = MatchStatus.CONFIRMED
    match.verified_at = datetime.now(timezone.utc)

    case: Case = match.case
    case.status = CaseStatus.FOUND

    # FRS FR-5.3: family alert (template fallback is always wired through llm_service).
    alert = llm_service.generate_family_alert(
        {
            "case_id": case.case_id,
            "person_name": case.person_name,
        },
        {"confidence_score": match.confidence_score, "tier": match.tier},
        session=db,
        actor_id=user.id,
    )

    audit_service.write_audit(
        db,
        action="match.confirm",
        actor_id=user.id,
        model_version=alert.get("model_version"),
        prompt_version=alert.get("prompt_version"),
        input_data={"match_id": str(match.id), "case_id": case.case_id},
        output_data={
            "family_notified": True,
            "provider_used": alert.get("provider"),
            "alert_preview": alert.get("text", "")[:120],
        },
        confidence_score=match.confidence_score,
    )
    db.commit()

    return ConfirmMatchResponse(
        confirmed=True,
        family_notified=True,
        provider_used=alert.get("provider", "template"),
        confidence_score=match.confidence_score,
        explanation=_explanation(match.tier, match.confidence_score),
    )


def _compute_error_vector(predicted_embedding: list[float] | None, actual_embedding: list[float]) -> dict:
    """Return a per-feature error dict.

    If the predicted embedding is available we compute |Δ| per dimension then
    bucket into the five facial feature groups (FRS §11 stage 3). When the
    predicted embedding is absent (pipeline hasn't yet run the aged-photo
    embed step) we record zeros so the row is still valid for audit.
    """
    if not predicted_embedding or not actual_embedding:
        return {
            "nose": 0.0,
            "cheekbone": 0.0,
            "jawline": 0.0,
            "eye_spacing": 0.0,
            "forehead_width": 0.0,
        }
    a = np.asarray(predicted_embedding, dtype=np.float64)
    b = np.asarray(actual_embedding, dtype=np.float64)
    if a.shape != b.shape or a.size == 0:
        return {
            "nose": 0.0,
            "cheekbone": 0.0,
            "jawline": 0.0,
            "eye_spacing": 0.0,
            "forehead_width": 0.0,
        }
    diff = np.abs(a - b)
    groups = np.array_split(diff, 5)
    names = ("nose", "cheekbone", "jawline", "eye_spacing", "forehead_width")
    return {name: float(group.mean()) for name, group in zip(names, groups)}


@router.post("/{match_id}/not-match", response_model=NotMatchResponse)
async def not_match(
    match_id: str,
    real_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FIELD_WORKER, UserRole.ADMIN)),
) -> NotMatchResponse:
    # FRS FR-5.4: real_photo mandatory. Reject empty uploads with 400.
    content = await real_photo.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail="A photograph of the actual individual is mandatory (FRS FR-5.4).",
        )

    match = _load_match_for_worker(db, match_id, user)
    if match.status != MatchStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Match is already {match.status}.")

    settings = get_settings()
    try:
        real_url = supabase_service.upload_photo(
            content,
            bucket=settings.supabase_bucket_not_match_photos,
            case_id=match.case_id,
            filename=real_photo.filename,
            content_type=real_photo.content_type,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("not-match photo upload failed")
        raise HTTPException(status_code=502, detail="Photo storage is temporarily unavailable.") from exc

    predicted_embedding: list[float] | None = None
    aged_photo = db.execute(
        select(Photo)
        .where(Photo.case_id == match.case_id, Photo.is_predicted_aged.is_(True))
        .order_by(Photo.created_at.desc())
    ).scalars().first()
    if aged_photo and aged_photo.embedding:
        predicted_embedding = list(aged_photo.embedding)

    actual_embedding = list(match.candidate_photo.embedding or []) if match.candidate_photo else []
    error_vector = _compute_error_vector(predicted_embedding, actual_embedding)

    feedback = NotMatchFeedback(
        match_id=match.id,
        real_photo_url=real_url,
        error_vector=error_vector,
    )
    db.add(feedback)

    match.status = MatchStatus.NOT_MATCH
    match.verified_at = datetime.now(timezone.utc)

    case: Case = match.case
    case.status = CaseStatus.ACTIVE  # FRS FR-5.5: reopen

    db.flush()
    pool_size = db.execute(select(func.count(NotMatchFeedback.id))).scalar_one()
    training_triggered = pool_size % FINE_TUNE_TRIGGER_COUNT == 0 and pool_size > 0

    audit_service.write_audit(
        db,
        action="match.not_match",
        actor_id=user.id,
        model_version=None,
        prompt_version=None,
        input_data={"match_id": str(match.id), "case_id": case.case_id},
        output_data={
            "feedback_id": str(feedback.id),
            "feedback_pool_size": pool_size,
            "training_cycle_triggered": training_triggered,
        },
        confidence_score=match.confidence_score,
    )
    db.commit()

    return NotMatchResponse(
        error_vector_captured=True,
        case_reopened=True,
        feedback_pool_size=pool_size,
        training_cycle_triggered=training_triggered,
        confidence_score=match.confidence_score,
        explanation=_explanation(match.tier, match.confidence_score),
    )
