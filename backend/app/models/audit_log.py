"""Tamper-evident audit log (FRS §10.3).

Append-only at the model layer: UPDATE and DELETE attempts raise
``AuditLogImmutableError`` via SQLAlchemy session flush hooks.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Uuid, event
from sqlalchemy.orm import Mapped, Session, mapped_column

_BigAutoInt = BigInteger().with_variant(Integer(), "sqlite")

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLogImmutableError(RuntimeError):
    """Raised when a caller attempts to update or delete an AuditLog row."""


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(_BigAutoInt, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hmac_signature: Mapped[str] = mapped_column(String(64), nullable=False)


@event.listens_for(Session, "before_flush")
def _enforce_audit_log_append_only(session: Session, _flush_context, _instances) -> None:
    for obj in session.dirty:
        if isinstance(obj, AuditLog) and session.is_modified(obj, include_collections=False):
            raise AuditLogImmutableError("AuditLog rows are append-only; UPDATE is forbidden.")
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise AuditLogImmutableError("AuditLog rows are append-only; DELETE is forbidden.")
