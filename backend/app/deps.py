"""FastAPI dependencies — DB session, JWT auth, role guards, app-settings cache.

Every router reads only through these dependencies. Tests override ``get_db``
to point at an in-memory SQLite session.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Iterator

from cachetools import TTLCache
from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_sessionmaker
from app.models import AppSettings, User, UserRole

logger = logging.getLogger(__name__)


# ─── database session ──────────────────────────────────────────────────────
def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


# ─── JWT issuing + validation ──────────────────────────────────────────────
def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expiry_hours * 3600
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def _decode(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = _decode(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject.")
    try:
        user_id = uuid.UUID(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.") from exc
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    allowed = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(sorted(allowed))}.",
            )
        return user

    return dependency


# ─── app_settings cache (60 s TTL, FRS §6.6 Tab 4) ─────────────────────────
_SETTINGS_CACHE: TTLCache[str, dict] = TTLCache(maxsize=1, ttl=60)
_SETTINGS_KEY = "app_settings"

_DEFAULTS: dict[str, object] = {
    "confidence_threshold": 0.60,
    "auto_alert_threshold": 0.80,
    "gpt4o_enabled": True,
    "geo_clustering_enabled": True,
}


def seed_app_settings_defaults(db: Session) -> None:
    """Insert any missing admin-tunable setting with its FRS default."""
    for key, value in _DEFAULTS.items():
        if db.get(AppSettings, key) is None:
            db.add(AppSettings(key=key, value=value))
    db.commit()


def load_app_settings(db: Session) -> dict:
    cached = _SETTINGS_CACHE.get(_SETTINGS_KEY)
    if cached is not None:
        return cached
    rows = db.execute(select(AppSettings)).scalars().all()
    merged = dict(_DEFAULTS)
    for row in rows:
        merged[row.key] = row.value
    _SETTINGS_CACHE[_SETTINGS_KEY] = merged
    return merged


def invalidate_app_settings_cache() -> None:
    _SETTINGS_CACHE.clear()


# ─── request ID helper (middleware attaches it) ────────────────────────────
def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


# ─── role aliases for decorators ───────────────────────────────────────────
ROLE_FAMILY = UserRole.FAMILY
ROLE_FIELD_WORKER = UserRole.FIELD_WORKER
ROLE_ADMIN = UserRole.ADMIN
