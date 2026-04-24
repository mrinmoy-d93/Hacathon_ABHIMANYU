from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole:
    FAMILY = "family"
    FIELD_WORKER = "field_worker"
    ADMIN = "admin"
    ALL = (FAMILY, FIELD_WORKER, ADMIN)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum(*UserRole.ALL, name="user_role", native_enum=False, validate_strings=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    cases: Mapped[list["Case"]] = relationship(back_populates="creator", foreign_keys="Case.created_by")  # noqa: F821
    verified_matches: Mapped[list["Match"]] = relationship(  # noqa: F821
        back_populates="field_worker", foreign_keys="Match.field_worker_id"
    )
