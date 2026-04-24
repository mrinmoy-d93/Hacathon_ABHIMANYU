from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CaseStatus:
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    FOUND = "found"
    CLOSED = "closed"
    ALL = (ACTIVE, UNDER_REVIEW, FOUND, CLOSED)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    # FRS FR-1.3: case_id format `KHJ-YYYY-XXXXX` is the natural PK.
    case_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    person_name: Mapped[str] = mapped_column(String(255), nullable=False)
    year_missing: Mapped[int] = mapped_column(Integer, nullable=False)
    age_at_disappearance: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen_location: Mapped[str] = mapped_column(String(255), nullable=False)
    identifying_marks: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(*CaseStatus.ALL, name="case_status", native_enum=False, validate_strings=True),
        nullable=False,
        default=CaseStatus.ACTIVE,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    creator: Mapped["User | None"] = relationship(back_populates="cases", foreign_keys=[created_by])  # noqa: F821
    photos: Mapped[list["Photo"]] = relationship(  # noqa: F821
        back_populates="case", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(  # noqa: F821
        back_populates="case", cascade="all, delete-orphan"
    )

    @property
    def predicted_current_age(self) -> int:
        """FRS FR-2.2: age_at_disappearance + (current_year - year_missing)."""
        return self.age_at_disappearance + (datetime.now(timezone.utc).year - self.year_missing)
