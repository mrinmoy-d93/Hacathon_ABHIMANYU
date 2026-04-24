"""/health — liveness + provider-configured signals (FRS NFR-2, NFR-8)."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_db
from app.schemas.health import HealthResponse, ProviderHealth

router = APIRouter()

_BOOT_TS = time.monotonic()


@router.get("/health", tags=["health"], response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    providers = ProviderHealth(
        openai=bool(settings.openai_api_key),
        groq=bool(settings.groq_api_key),
        hf=bool(settings.hf_token),
        replicate=bool(getattr(settings, "replicate_api_token", "") or ""),
    )

    # Legacy callers still expect status=="ok"; keep the contract stable.
    status_text = "ok" if db_ok else "degraded"
    return HealthResponse(
        status=status_text,
        db=db_ok,
        providers=providers,
        version=settings.app_version,
        uptime_seconds=round(time.monotonic() - _BOOT_TS, 3),
    )
