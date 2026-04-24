"""/cases — missing-person case CRUD + AI pipeline trigger (FRS §6.2, §6.3).

Thin HTTP layer:
* Row persistence + ID minting is delegated to ``app.utils.case_id`` and the ORM.
* Photo upload is delegated to ``supabase_service.upload_photo``.
* AI processing is delegated to ``pipeline_service.process_case`` (async via
  ``BackgroundTasks``).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_current_user, get_db, require_role
from app.models import Case, CaseStatus, Photo, User, UserRole
from app.schemas.case import (
    CaseCreate,
    CaseCreateResponse,
    CaseDetail,
    CaseResult,
    CaseResultMatch,
    ConfidenceDistribution,
    MatchSummary,
    PhotoOut,
    PhotoUploadResponse,
    ProcessResponse,
)
from app.services import audit_service, pipeline_service, supabase_service
from app.services.ai_common import InsufficientPhotosError
from app.utils.case_id import generate_case_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Per-process job status store. Keyed by case_id; latest run wins.
_JOB_STATUS: dict[str, dict] = {}


def _explanation(tier: str | None, score: float | None) -> str:
    """Plain-language explanation (FRS FR-4.2, FR-4.4)."""
    if score is None:
        return (
            "This is an estimate produced by Artificial Intelligence (AI). "
            "No match has been computed yet."
        )
    band = tier or "unknown"
    return (
        f"Confidence is {score:.0%} ({band}). "
        "This is an estimate produced by Artificial Intelligence (AI). "
        "Please have the result verified by a certified officer before acting upon it."
    )


def _load_case_or_404(db: Session, case_id: str) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


def _can_view_case(user: User, case: Case) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if case.created_by == user.id:
        return True
    if user.role == UserRole.FIELD_WORKER:
        assigned = any(m.field_worker_id == user.id for m in case.matches)
        return assigned
    return False


@router.post(
    "",
    response_model=CaseCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.FAMILY, UserRole.ADMIN)),
) -> CaseCreateResponse:
    current_year = datetime.now(timezone.utc).year
    if payload.year_missing > current_year:
        raise HTTPException(status_code=400, detail="year_missing cannot be in the future.")

    case_id = generate_case_id(db, payload.year_missing)
    case = Case(
        case_id=case_id,
        person_name=payload.person_name,
        year_missing=payload.year_missing,
        age_at_disappearance=payload.age_at_disappearance,
        last_seen_location=payload.last_seen_location,
        identifying_marks=payload.identifying_marks,
        status=CaseStatus.ACTIVE,
        created_by=user.id,
    )
    db.add(case)
    db.flush()

    audit_service.write_audit(
        db,
        action="case.create",
        actor_id=user.id,
        model_version=None,
        prompt_version=None,
        input_data={"person_name": payload.person_name, "year_missing": payload.year_missing},
        output_data={"case_id": case_id, "predicted_current_age": case.predicted_current_age},
    )
    db.commit()

    return CaseCreateResponse(case_id=case_id, predicted_current_age=case.predicted_current_age)


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseDetail:
    case = _load_case_or_404(db, case_id)
    if not _can_view_case(user, case):
        raise HTTPException(status_code=403, detail="You do not have access to this case.")

    return CaseDetail(
        case_id=case.case_id,
        person_name=case.person_name,
        year_missing=case.year_missing,
        age_at_disappearance=case.age_at_disappearance,
        predicted_current_age=case.predicted_current_age,
        last_seen_location=case.last_seen_location,
        identifying_marks=case.identifying_marks,
        status=case.status,
        created_at=case.created_at,
        photos=[
            PhotoOut(
                id=str(p.id),
                supabase_url=p.supabase_url,
                age_at_photo=p.age_at_photo,
                is_predicted_aged=p.is_predicted_aged,
            )
            for p in case.photos
        ],
        matches=[
            MatchSummary(
                id=str(m.id),
                candidate_photo_url=m.candidate_photo.supabase_url if m.candidate_photo else "",
                confidence_score=m.confidence_score,
                tier=m.tier,
                status=m.status,
            )
            for m in case.matches
        ],
    )


@router.post(
    "/{case_id}/photos",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    case_id: str,
    age_at_photo: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PhotoUploadResponse:
    case = _load_case_or_404(db, case_id)
    if case.created_by != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the case creator can upload photos.")
    if age_at_photo < 0 or age_at_photo > 120:
        raise HTTPException(status_code=400, detail="age_at_photo must be between 0 and 120.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    # FRS FR-2.4: 10 MB max.
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo exceeds the 10 MB upload limit.")

    settings = get_settings()
    try:
        public_url = supabase_service.upload_photo(
            content,
            bucket=settings.supabase_bucket_case_photos,
            case_id=case_id,
            filename=file.filename,
            content_type=file.content_type,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("supabase upload failed")
        raise HTTPException(status_code=502, detail="Photo storage is temporarily unavailable.") from exc

    photo = Photo(
        case_id=case_id,
        supabase_url=public_url,
        age_at_photo=age_at_photo,
        is_predicted_aged=False,
    )
    db.add(photo)
    db.flush()

    audit_service.write_audit(
        db,
        action="case.upload_photo",
        actor_id=user.id,
        model_version=None,
        prompt_version=None,
        input_data={"case_id": case_id, "age_at_photo": age_at_photo, "bytes": len(content)},
        output_data={"photo_id": str(photo.id)},
    )
    db.commit()

    return PhotoUploadResponse(photo_id=str(photo.id), supabase_url=public_url)


def _run_pipeline_background(case_id: str, actor_id: uuid.UUID | None) -> None:
    """Background job runner: builds its own Session so the request one is freed."""
    from app.db import get_sessionmaker

    session_factory = get_sessionmaker()
    job_key = case_id
    with session_factory() as session:
        try:
            result = pipeline_service.process_case(session, case_id, actor_id=actor_id)
            _JOB_STATUS[job_key] = {"status": "complete", "result": result}
        except Exception as exc:  # noqa: BLE001
            logger.exception("pipeline failed for case %s", case_id)
            _JOB_STATUS[job_key] = {"status": "error", "error": str(exc)}


@router.post("/{case_id}/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
def process_case(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProcessResponse:
    case = _load_case_or_404(db, case_id)
    if case.created_by != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the case creator can process this case.")

    source_photos = [p for p in case.photos if not p.is_predicted_aged]
    # FRS FR-2.3: min 2 photos.
    if len(source_photos) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two (2) source photographs are required before processing (FRS FR-2.3).",
        )

    job_id = str(uuid.uuid4())
    _JOB_STATUS[case_id] = {"status": "processing", "job_id": job_id}

    audit_service.write_audit(
        db,
        action="case.process_requested",
        actor_id=user.id,
        model_version=None,
        prompt_version=None,
        input_data={"case_id": case_id},
        output_data={"job_id": job_id},
    )
    db.commit()

    background_tasks.add_task(_run_pipeline_background, case_id, user.id)
    return ProcessResponse(status="processing", job_id=job_id)


@router.post(
    "/{case_id}/process-sync",
    response_model=CaseResult,
    include_in_schema=False,
)
def process_case_sync(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseResult:
    """Synchronous variant used only by tests. Not advertised in OpenAPI."""
    case = _load_case_or_404(db, case_id)
    if case.created_by != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the case creator can process this case.")
    source_photos = [p for p in case.photos if not p.is_predicted_aged]
    if len(source_photos) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two (2) source photographs are required before processing (FRS FR-2.3).",
        )
    try:
        result = pipeline_service.process_case(db, case_id, actor_id=user.id)
    except InsufficientPhotosError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _JOB_STATUS[case_id] = {"status": "complete", "result": result}
    return _result_payload(case_id)


def _result_payload(case_id: str) -> CaseResult:
    job = _JOB_STATUS.get(case_id, {"status": "unknown"})
    if job.get("status") != "complete":
        return CaseResult(
            status=job.get("status", "unknown"),
            aged_photo_url=None,
            matches=[],
            summary=None,
            confidence_distribution=ConfidenceDistribution(high=0, medium=0, low=0),
            providers_used={},
            processing_time_seconds=None,
            explanation=_explanation(None, None),
            confidence_score=None,
        )
    result = job["result"]
    raw_matches = result.get("matches", [])
    dist = ConfidenceDistribution(
        high=sum(1 for m in raw_matches if m["tier"] == "high"),
        medium=sum(1 for m in raw_matches if m["tier"] == "medium"),
        low=sum(1 for m in raw_matches if m["tier"] == "low"),
    )
    match_items = [
        CaseResultMatch(
            match_id=m.get("match_id"),
            candidate_photo_url=m["photo_url"],
            confidence_score=m["confidence"],
            tier=m["tier"],
            explanation=_explanation(m["tier"], m["confidence"]),
        )
        for m in raw_matches
    ]
    top_confidence = max((m["confidence"] for m in raw_matches), default=None)
    top_tier = next((m["tier"] for m in raw_matches), None)
    return CaseResult(
        status="complete",
        aged_photo_url=result.get("aged_photo_url"),
        matches=match_items,
        summary=result.get("summary"),
        confidence_distribution=dist,
        providers_used=dict(result.get("providers_used", {})),
        processing_time_seconds=result.get("processing_time_seconds"),
        explanation=_explanation(top_tier, top_confidence),
        confidence_score=top_confidence,
    )


@router.get("/{case_id}/result", response_model=CaseResult)
def get_case_result(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseResult:
    case = _load_case_or_404(db, case_id)
    if not _can_view_case(user, case):
        raise HTTPException(status_code=403, detail="You do not have access to this case.")
    return _result_payload(case_id)
