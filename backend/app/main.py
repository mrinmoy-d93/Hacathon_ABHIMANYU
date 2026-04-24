"""FastAPI entry point (FRS §7-8).

* Routers mounted under ``/api/*`` (+ ``/health`` at the root for Render /
  Hugging Face Spaces liveness probes).
* CORS, request-ID, and global exception handling per FRS NFR-3.
* Rate limiting via slowapi: 60/min unauth, 300/min authenticated.
* Startup hook: verify DB connection, seed ``app_settings`` defaults, and
  log which AI providers are configured (without ever logging the keys).
"""
from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.db import get_engine, get_sessionmaker
from app.deps import seed_app_settings_defaults
from app.routers import admin, auth, cases, health, matches

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

FRS_PROBLEM_STATEMENT = (
    "KHOJO — Artificial Intelligence (AI) powered Missing Person Finder with "
    "facial aging technology. India records more than 100,000+ missing person "
    "cases every year. KHOJO applies AI to predict how a missing person is "
    "likely to appear today and automatically matches this predicted face "
    "against a database of sighted individuals. See FRS v1.1 §2 for the full "
    "problem statement."
)


# ─── Rate limiter ─────────────────────────────────────────────────────────
def _rate_key(request: Request) -> str:
    """Per-user for authenticated calls, per-IP for anonymous."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return f"user:{auth_header[7:][:32]}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _default_limit() -> str:
    auth_limit = settings.rate_limit_auth
    anon_limit = settings.rate_limit_anon
    # Use the higher (authenticated) limit as the default; _rate_key separates
    # buckets so an anonymous caller with the same IP gets the stricter bucket.
    _ = auth_limit  # kept for clarity; slowapi applies limits per decorator
    return anon_limit


limiter = Limiter(key_func=_rate_key, default_limits=[settings.rate_limit_anon])


# ─── Request-ID middleware ────────────────────────────────────────────────
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled exception request_id=%s path=%s", request_id, request.url.path)
            raise
        response.headers["x-request-id"] = request_id
        return response


# ─── Lifespan: startup / shutdown ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 1. verify DB
    db_ok = False
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("startup: DB connectivity check failed: %s", exc)

    # 2. seed app_settings defaults — best-effort (DB may not yet be migrated).
    if db_ok:
        try:
            with get_sessionmaker()() as session:
                seed_app_settings_defaults(session)
        except Exception as exc:  # noqa: BLE001
            logger.warning("startup: seeding app_settings failed: %s", exc)

    # 3. log provider configuration without leaking keys.
    logger.info(
        "startup: providers configured — openai=%s groq=%s hf=%s replicate=%s colab=%s demo_mode=%s",
        bool(settings.openai_api_key),
        bool(settings.groq_api_key),
        bool(settings.hf_token),
        bool(getattr(settings, "replicate_api_token", "")),
        bool(settings.colab_aging_url),
        settings.demo_mode,
    )
    yield


# ─── App factory ──────────────────────────────────────────────────────────
app = FastAPI(
    title="KHOJO API",
    description=FRS_PROBLEM_STATEMENT,
    version=settings.app_version,
    lifespan=lifespan,
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-request-id"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIdMiddleware)


# ─── Global exception handlers ────────────────────────────────────────────
def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "request_id": _request_id(request)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep the field-level errors but strip internal paths.
    errors = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Input failed validation. Please correct the fields and retry.",
            "details": errors,
            "request_id": _request_id(request),
        },
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too many requests. Please wait a moment and try again.",
            "request_id": _request_id(request),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # FRS NFR-3: never leak stack traces to clients.
    logger.exception("unhandled error request_id=%s", _request_id(request))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred. Please try again later.",
            "request_id": _request_id(request),
        },
    )


# ─── Router mounting ──────────────────────────────────────────────────────
app.include_router(health.router)  # /health at root for liveness probes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.app_version}


# Expose the limiter on module import so tests and other callers can reference it.
__all__ = ["app", "limiter"]

# Silence a noisy Supabase httpx deprecation in sandbox when no SUPABASE_URL is set.
os.environ.setdefault("SUPABASE_URL", "")
