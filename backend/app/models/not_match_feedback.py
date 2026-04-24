from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotMatchFeedback(Base):
    """FRS §6.5 / §11: "Not a Match" real photo + per-feature error vector.

    Populated when a field worker rejects a match; 50 rows trigger a model
    fine-tune.
    """

    __tablename__ = "not_match_feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("matches.id"), nullable=False, unique=True, index=True
    )
    real_photo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    error_vector: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    match: Mapped["Match"] = relationship(back_populates="not_match_feedback")  # noqa: F821
