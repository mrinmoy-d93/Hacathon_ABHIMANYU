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
os.environ.setdefault("USE_MOCK_AI", "true")

from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.ai_common import CircuitBreaker  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_settings_and_breakers():
    """Clear the settings cache and reset every circuit breaker before each test."""
    get_settings.cache_clear()
    # Reset breakers that are module-level singletons.
    from app.services import aging_service, llm_service

    for breaker in (
        aging_service._HF_BREAKER,
        aging_service._COLAB_BREAKER,
        llm_service._OPENAI_BREAKER,
        llm_service._GROQ_BREAKER,
    ):
        if isinstance(breaker, CircuitBreaker):
            breaker.reset()

    yield
    get_settings.cache_clear()


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


@pytest.fixture
def real_mode(monkeypatch):
    """Force USE_MOCK_AI=false for a single test."""
    monkeypatch.setenv("USE_MOCK_AI", "false")
    get_settings.cache_clear()
    yield


@pytest.fixture
def fast_retries(monkeypatch):
    """Shrink tenacity waits to near-zero so provider-failure tests don't sleep."""
    from app.services import aging_service, llm_service

    monkeypatch.setattr(aging_service, "RETRY_WAIT_MIN", 0.0, raising=False)
    monkeypatch.setattr(aging_service, "RETRY_WAIT_MAX", 0.0, raising=False)
    monkeypatch.setattr(aging_service, "RETRY_ATTEMPTS", 2, raising=False)
    monkeypatch.setattr(llm_service, "RETRY_WAIT_MIN", 0.0, raising=False)
    monkeypatch.setattr(llm_service, "RETRY_WAIT_MAX", 0.0, raising=False)
    monkeypatch.setattr(llm_service, "RETRY_ATTEMPTS", 2, raising=False)
    yield
