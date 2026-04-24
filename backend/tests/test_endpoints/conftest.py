"""Shared fixtures for all /api/* router tests.

* One StaticPool in-memory SQLite engine per test keeps schema + data isolated.
* ``get_db`` is overridden to yield a scoped session against that engine.
* Helper fixtures create test users and issue JWTs so individual tests can
  grab a pre-authenticated TestClient.
"""
from __future__ import annotations

import uuid
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.deps import create_access_token, get_db, invalidate_app_settings_cache
from app.main import app
from app.models import Base, User, UserRole


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session_factory(db_engine):
    return sessionmaker(bind=db_engine, expire_on_commit=False, future=True)


@pytest.fixture
def db_session(db_session_factory):
    with db_session_factory() as s:
        yield s


@pytest.fixture
def client(db_session_factory, monkeypatch) -> TestClient:
    def _get_db():
        session = db_session_factory()
        try:
            yield session
        finally:
            session.close()

    # Make any `get_sessionmaker()` lookup (e.g. background tasks) return the
    # same test factory so the in-memory data is visible across sessions.
    from app import db as db_module

    monkeypatch.setattr(db_module, "get_sessionmaker", lambda: db_session_factory)
    app.dependency_overrides[get_db] = _get_db
    invalidate_app_settings_cache()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        invalidate_app_settings_cache()


# ─── user / auth helpers ───────────────────────────────────────────────────
def _make_user(db: Session, *, role: str, name: str, phone: str, location: str = "Ahmedabad") -> User:
    user = User(id=uuid.uuid4(), name=name, phone=phone, location=location, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def make_user(db_session_factory) -> Callable[..., User]:
    def _factory(role: str, phone: str | None = None, name: str | None = None) -> User:
        with db_session_factory() as s:
            return _make_user(
                s,
                role=role,
                name=name or f"User-{role}",
                phone=phone or f"+9199000{uuid.uuid4().int % 100000:05d}",
            )

    return _factory


@pytest.fixture
def family_user(make_user) -> User:
    return make_user(UserRole.FAMILY, phone="+919900000001", name="Family User")


@pytest.fixture
def field_worker_user(make_user) -> User:
    return make_user(UserRole.FIELD_WORKER, phone="+919900000002", name="Field Worker")


@pytest.fixture
def admin_user(make_user) -> User:
    return make_user(UserRole.ADMIN, phone="+919900000003", name="Admin User")


@pytest.fixture
def auth_headers() -> Callable[[User], dict]:
    def _factory(user: User) -> dict:
        token, _ = create_access_token(str(user.id), user.role)
        return {"Authorization": f"Bearer {token}"}

    return _factory
