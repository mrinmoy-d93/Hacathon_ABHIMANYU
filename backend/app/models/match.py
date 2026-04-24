from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MatchTier:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ALL = (HIGH, MEDIUM, LOW)


class MatchStatus:
    PENDING = "pending"
    CONFIRMED = "confirmed"
    NOT_MATCH = "not_match"
    ALL = (PENDING, CONFIRMED, NOT_MATCH)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(16), ForeignKey("cases.case_id"), nullable=False, index=True)
    candidate_photo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("photos.id"), nullable=False, index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(
        Enum(*MatchTier.ALL, name="match_tier", native_enum=False, validate_strings=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(*MatchStatus.ALL, name="match_status", native_enum=False, validate_strings=True),
        nullable=False,
        default=MatchStatus.PENDING,
    )
    field_worker_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case: Mapped["Case"] = relationship(back_populates="matches")  # noqa: F821
    candidate_photo: Mapped["Photo"] = relationship(  # noqa: F821
        back_populates="matches", foreign_keys=[candidate_photo_id]
    )
    field_worker: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="verified_matches", foreign_keys=[field_worker_id]
    )
    not_match_feedback: Mapped["NotMatchFeedback | None"] = relationship(  # noqa: F821
        back_populates="match", cascade="all, delete-orphan", uselist=False
    )
