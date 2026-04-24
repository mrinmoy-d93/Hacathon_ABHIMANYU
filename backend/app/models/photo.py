from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(16), ForeignKey("cases.case_id"), nullable=False, index=True)
    supabase_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    age_at_photo: Mapped[int] = mapped_column(Integer, nullable=False)
    # 512-dim L2-normalised ArcFace embedding, stored as JSONB on Postgres.
    embedding: Mapped[list[float] | None] = mapped_column(JSONType, nullable=True)
    is_predicted_aged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    case: Mapped["Case"] = relationship(back_populates="photos")  # noqa: F821
    matches: Mapped[list["Match"]] = relationship(  # noqa: F821
        back_populates="candidate_photo", foreign_keys="Match.candidate_photo_id"
    )
