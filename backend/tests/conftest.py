from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Ensure `backend/` is on the import path when pytest is invoked from the repo root.
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Populate env before app.config is imported anywhere.
os.environ.setdefault("AUDIT_SIGNING_SECRET", "test-secret-" + "a" * 48)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")

from app.models import Base  # noqa: E402


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", future=True)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
