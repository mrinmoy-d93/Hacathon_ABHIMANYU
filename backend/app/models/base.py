"""SQLAlchemy declarative base and cross-dialect type helpers.

The models must run unchanged against both PostgreSQL (Supabase in prod) and
in-memory SQLite (pytest). This module centralises the portable type shims.
"""
from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


JSONType = JSON().with_variant(JSONB(), "postgresql")
