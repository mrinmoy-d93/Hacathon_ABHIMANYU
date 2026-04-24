"""/admin — administrator console (FRS §6.6 five tabs).

Every endpoint requires admin role via :func:`require_role`. State-changing
routes write audit entries through :mod:`app.services.audit_service`.
Settings PATCH invalidates the in-process cache so admin-console tweaks take
effect on the next request (FRS §6.6 Tab 4 "no code deployment required").
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import (
    get_db,
    invalidate_app_settings_cache,
    load_app_settings,
    require_role,
)
from app.models import (
    AppSettings,
    AuditLog,
    Case,
    CaseStatus,
    Match,
    MatchStatus,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminActionResponse,
    AdminCaseRejectRequest,
    AdminCaseRow,
    AdminCasesPage,
    AdminDashboard,
    AuditEntry,
    AuditLogPage,
    ConfidenceDistribution,
    FieldWorkerAssign,
    FieldWorkerRow,
    FieldWorkerUpdate,
    RecentActivityItem,
    SettingsOut,
    SettingsUpdate,
)
from app.services import audit_service

logger = logging.getLogger(__name__)

router = APIRouter()

_admin_only = require_role(UserRole.ADMIN)


# ─── Tab 1: Dashboard ──────────────────────────────────────────────────────
@router.get("/dashboard", response_model=AdminDashboard)
def dashboard(db: Session = Depends(get_db), _: User = Depends(_admin_only)) -> AdminDashboard:
    total_cases = db.execute(select(func.count(Case.case_id))).scalar_one()
    active = db.execute(
        select(func.count(Case.case_id)).where(Case.status == CaseStatus.ACTIVE)
    ).scalar_one()
    matches_found = db.execute(
        select(func.count(Match.id)).where(Match.status == MatchStatus.CONFIRMED)
    ).scalar_one()
    review_pending = db.execute(
        select(func.count(Match.id)).where(Match.status == MatchStatus.PENDING, Match.tier == "medium")
    ).scalar_one()

    high = db.execute(select(func.count(Match.id)).where(Match.tier == "high")).scalar_one()
    medium = db.execute(select(func.count(Match.id)).where(Match.tier == "medium")).scalar_one()
    low = db.execute(select(func.count(Match.id)).where(Match.tier == "low")).scalar_one()

    recent_rows = db.execute(
        select(AuditLog).order_by(AuditLog.id.desc()).limit(10)
    ).scalars().all()

    return AdminDashboard(
        total_cases=total_cases,
        active_searches=active,
        matches_found=matches_found,
        review_pending=review_pending,
        confidence_distribution=ConfidenceDistribution(high=high, medium=medium, low=low),
        recent_activity=[
            RecentActivityItem(
                id=row.id,
                action=row.action,
                timestamp=row.timestamp,
                confidence_score=row.confidence_score,
            )
            for row in recent_rows
        ],
    )


# ─── Tab 2: Case management ────────────────────────────────────────────────
@router.get("/cases", response_model=AdminCasesPage)
def list_cases(
    status: str | None = Query(default=None, pattern=r"^(active|under_review|found|closed)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
) -> AdminCasesPage:
    base = select(Case)
    count_stmt = select(func.count(Case.case_id))
    if status is not None:
        base = base.where(Case.status == status)
        count_stmt = count_stmt.where(Case.status == status)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(
        base.order_by(Case.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    items: list[AdminCaseRow] = []
    for case in rows:
        top_match = db.execute(
            select(Match)
            .where(Match.case_id == case.case_id)
            .order_by(Match.confidence_score.desc())
            .limit(1)
        ).scalar_one_or_none()
        items.append(
            AdminCaseRow(
                case_id=case.case_id,
                person_name=case.person_name,
                status=case.status,
                predicted_current_age=case.predicted_current_age,
                last_seen_location=case.last_seen_location,
                confidence_score=top_match.confidence_score if top_match else None,
                assigned_field_worker_id=str(top_match.field_worker_id) if top_match and top_match.field_worker_id else None,
            )
        )
    return AdminCasesPage(items=items, page=page, page_size=page_size, total=total)


@router.post("/cases/{case_id}/approve", response_model=AdminActionResponse)
def approve_case(
    case_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
) -> AdminActionResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    case.status = CaseStatus.UNDER_REVIEW

    audit_service.write_audit(
        db,
        action="admin.case.approve",
        actor_id=admin.id,
        model_version=None,
        prompt_version=None,
        input_data={"case_id": case_id},
        output_data={"status": case.status},
    )
    db.commit()
    return AdminActionResponse(case_id=case_id, action="approve", status=case.status)


@router.post("/cases/{case_id}/reject", response_model=AdminActionResponse)
def reject_case(
    case_id: str,
    payload: AdminCaseRejectRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
) -> AdminActionResponse:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    case.status = CaseStatus.CLOSED

    audit_service.write_audit(
        db,
        action="admin.case.reject",
        actor_id=admin.id,
        model_version=None,
        prompt_version=None,
        input_data={"case_id": case_id, "reason": payload.reason},
        output_data={"status": case.status},
    )
    db.commit()
    return AdminActionResponse(case_id=case_id, action="reject", status=case.status)


# ─── Tab 3: Field-worker management ────────────────────────────────────────
@router.get("/field-workers", response_model=list[FieldWorkerRow])
def list_field_workers(db: Session = Depends(get_db), _: User = Depends(_admin_only)) -> list[FieldWorkerRow]:
    workers = db.execute(select(User).where(User.role == UserRole.FIELD_WORKER)).scalars().all()
    result: list[FieldWorkerRow] = []
    for worker in workers:
        verified = db.execute(
            select(func.count(Match.id)).where(
                Match.field_worker_id == worker.id,
                Match.status.in_([MatchStatus.CONFIRMED, MatchStatus.NOT_MATCH]),
            )
        ).scalar_one()
        confirmed = db.execute(
            select(func.count(Match.id)).where(
                Match.field_worker_id == worker.id, Match.status == MatchStatus.CONFIRMED
            )
        ).scalar_one()
        accuracy = (confirmed / verified) if verified else 0.0
        result.append(
            FieldWorkerRow(
                id=str(worker.id),
                name=worker.name,
                zone=worker.location,
                verification_count=verified,
                accuracy_score=round(accuracy, 4),
            )
        )
    return result


@router.post("/field-workers", response_model=FieldWorkerRow, status_code=status.HTTP_201_CREATED)
def assign_field_worker(
    payload: FieldWorkerAssign,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
) -> FieldWorkerRow:
    try:
        user_uuid = uuid.UUID(payload.user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="user_id must be a UUID.") from exc
    target = db.get(User, user_uuid)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    target.role = UserRole.FIELD_WORKER
    target.location = payload.zone

    audit_service.write_audit(
        db,
        action="admin.field_worker.assign",
        actor_id=admin.id,
        model_version=None,
        prompt_version=None,
        input_data={"user_id": payload.user_id, "zone": payload.zone},
        output_data={"role": target.role, "zone": target.location},
    )
    db.commit()
    return FieldWorkerRow(
        id=str(target.id),
        name=target.name,
        zone=target.location,
        verification_count=0,
        accuracy_score=0.0,
    )


@router.patch("/field-workers/{worker_id}", response_model=FieldWorkerRow)
def update_field_worker(
    worker_id: str,
    payload: FieldWorkerUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
) -> FieldWorkerRow:
    try:
        worker_uuid = uuid.UUID(worker_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="worker_id must be a UUID.") from exc
    worker = db.get(User, worker_uuid)
    if worker is None or worker.role != UserRole.FIELD_WORKER:
        raise HTTPException(status_code=404, detail="Field worker not found.")

    if payload.zone is not None:
        worker.location = payload.zone
    if payload.leave_status == "on_leave":
        # Reassign any open matches away from this worker.
        open_matches = db.execute(
            select(Match).where(
                Match.field_worker_id == worker.id, Match.status == MatchStatus.PENDING
            )
        ).scalars().all()
        other = db.execute(
            select(User)
            .where(User.role == UserRole.FIELD_WORKER, User.id != worker.id)
            .limit(1)
        ).scalar_one_or_none()
        for m in open_matches:
            m.field_worker_id = other.id if other else None

    audit_service.write_audit(
        db,
        action="admin.field_worker.update",
        actor_id=admin.id,
        model_version=None,
        prompt_version=None,
        input_data={"worker_id": worker_id, "zone": payload.zone, "leave_status": payload.leave_status},
        output_data={"zone": worker.location, "leave_status": payload.leave_status},
    )
    db.commit()
    return FieldWorkerRow(
        id=str(worker.id),
        name=worker.name,
        zone=worker.location,
        verification_count=0,
        accuracy_score=0.0,
    )


# ─── Tab 4: AI settings (no-code threshold tuning) ─────────────────────────
def _settings_payload(db: Session) -> SettingsOut:
    merged = load_app_settings(db)
    return SettingsOut(
        confidence_threshold=float(merged["confidence_threshold"]),
        auto_alert_threshold=float(merged["auto_alert_threshold"]),
        gpt4o_enabled=bool(merged["gpt4o_enabled"]),
        geo_clustering_enabled=bool(merged["geo_clustering_enabled"]),
        current_model_version=get_settings().current_model_version,
    )


@router.get("/settings", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db), _: User = Depends(_admin_only)) -> SettingsOut:
    return _settings_payload(db)


@router.patch("/settings", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_only),
) -> SettingsOut:
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No settings provided to update.")

    # Enforce confidence < auto_alert (nonsensical otherwise).
    merged = load_app_settings(db)
    merged.update(updates)
    if float(merged["confidence_threshold"]) >= float(merged["auto_alert_threshold"]):
        raise HTTPException(
            status_code=400,
            detail="confidence_threshold must be strictly less than auto_alert_threshold.",
        )

    for key, value in updates.items():
        row = db.get(AppSettings, key)
        if row is None:
            row = AppSettings(key=key, value=value, updated_by=admin.id)
            db.add(row)
        else:
            row.value = value
            row.updated_by = admin.id

    invalidate_app_settings_cache()

    audit_service.write_audit(
        db,
        action="admin.settings.update",
        actor_id=admin.id,
        model_version=None,
        prompt_version=None,
        input_data=updates,
        output_data=updates,
    )
    db.commit()
    return _settings_payload(db)


# ─── Tab 5: Audit log ──────────────────────────────────────────────────────
def _parse_date(value: str | None, name: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} must be ISO-8601.") from exc


def _audit_window(from_: str | None, to: str | None) -> tuple[datetime | None, datetime | None]:
    return _parse_date(from_, "from"), _parse_date(to, "to")


@router.get("/audit-log", response_model=AuditLogPage)
def read_audit_log(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
) -> AuditLogPage:
    from_dt, to_dt = _audit_window(from_, to)
    conditions = []
    if from_dt is not None:
        conditions.append(AuditLog.timestamp >= from_dt)
    if to_dt is not None:
        conditions.append(AuditLog.timestamp <= to_dt)

    count_stmt = select(func.count(AuditLog.id))
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = db.execute(count_stmt).scalar_one()

    stmt = select(AuditLog)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(stmt).scalars().all()
    items = [
        AuditEntry(
            id=row.id,
            timestamp=row.timestamp,
            actor_id=str(row.actor_id) if row.actor_id else None,
            action=row.action,
            model_version=row.model_version,
            confidence_score=row.confidence_score,
            input_hash=row.input_hash,
            output_hash=row.output_hash,
        )
        for row in rows
    ]
    return AuditLogPage(items=items, page=page, page_size=page_size, total=total)


def _csv_stream(db: Session, from_dt: datetime | None, to_dt: datetime | None) -> Iterator[bytes]:
    # Delegate the redacted CSV rendering to audit_service so the PII rules live
    # in one place (FRS §10.2). Stream in a single chunk for simplicity — audit
    # exports are typically small.
    yield audit_service.export_audit_csv(db, from_date=from_dt, to_date=to_dt).encode("utf-8")


@router.get("/audit-log/export")
def export_audit_log(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    format: str = Query(default="csv", pattern=r"^(csv)$"),
    db: Session = Depends(get_db),
    _: User = Depends(_admin_only),
):
    from_dt, to_dt = _audit_window(from_, to)
    filename = f"khojo-audit-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(_csv_stream(db, from_dt, to_dt), media_type="text/csv", headers=headers)
