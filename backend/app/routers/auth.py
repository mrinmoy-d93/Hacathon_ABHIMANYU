"""/auth — registration + OTP-based authentication (FRS §7.1).

Thin HTTP wrapper: all persistence is delegated to the ORM, OTP state lives in
an in-memory per-process dict (replaceable with Redis in production, noted in
`docs/DEMO_MODE.md`). Every state-changing endpoint writes an audit entry.
"""
from __future__ import annotations

import logging
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import create_access_token, get_db
from app.models import User, UserRole
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    SendOtpRequest,
    SendOtpResponse,
    UserOut,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services import audit_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Hackathon demo admin ID. Compared in constant time via ``secrets.compare_digest``.
# Production would store a per-admin bcrypt hash on the User row; that migration
# is noted in FRS §10.2 but out of scope here.
_DEMO_ADMIN_POLICE_ID = "KHOJO-ADMIN-2026"

# Per-phone OTP store {phone: (otp, expires_at_epoch)}. Per-process only — the
# production deployment substitutes Redis (see FRS §7.1 rate-limit guidance).
_OTP_STORE: dict[str, tuple[str, float]] = {}
_OTP_TTL_SECONDS = 300


def _otp_is_valid(phone: str, otp: str) -> bool:
    settings = get_settings()
    if settings.demo_mode and otp == settings.demo_otp:
        return True
    record = _OTP_STORE.get(phone)
    if not record:
        return False
    stored, expires_at = record
    if time.monotonic() > expires_at:
        _OTP_STORE.pop(phone, None)
        return False
    if not secrets.compare_digest(stored, otp):
        return False
    _OTP_STORE.pop(phone, None)
    return True


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    if payload.role not in UserRole.ALL:
        raise HTTPException(status_code=400, detail="Unknown role.")

    existing = db.execute(select(User).where(User.phone == payload.phone)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A user is already registered with this phone number.")

    user = User(
        id=uuid.uuid4(),
        name=payload.name,
        phone=payload.phone,
        location=payload.location,
        role=payload.role,
    )
    db.add(user)
    db.flush()

    audit_service.write_audit(
        db,
        action="auth.register",
        actor_id=user.id,
        model_version=None,
        prompt_version=None,
        input_data={"phone": payload.phone, "role": payload.role, "location": payload.location},
        output_data={"user_id": str(user.id), "role": user.role},
    )
    db.commit()
    return RegisterResponse(user_id=str(user.id))


@router.post("/send-otp", response_model=SendOtpResponse)
def send_otp(payload: SendOtpRequest, db: Session = Depends(get_db)) -> SendOtpResponse:
    settings = get_settings()

    if settings.demo_mode:
        logger.info("demo_mode: skipping SMS; fixed OTP %s for %s", settings.demo_otp, payload.phone)
    else:
        code = f"{secrets.randbelow(1_000_000):06d}"
        _OTP_STORE[payload.phone] = (code, time.monotonic() + _OTP_TTL_SECONDS)
        # In production this would dispatch via Twilio / MSG91. We deliberately
        # never log the plain OTP (FRS §10.2 privacy).
        logger.info("OTP generated for %s (not logged)", payload.phone)

    audit_service.write_audit(
        db,
        action="auth.send_otp",
        actor_id=None,
        model_version=None,
        prompt_version=None,
        input_data={"phone": payload.phone, "demo_mode": settings.demo_mode},
        output_data={"otp_sent": True},
    )
    db.commit()
    return SendOtpResponse(otp_sent=True, demo_mode=settings.demo_mode)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)) -> VerifyOtpResponse:
    if not _otp_is_valid(payload.phone, payload.otp):
        raise HTTPException(status_code=401, detail="OTP is invalid or has expired.")

    user = db.execute(select(User).where(User.phone == payload.phone)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="No user is registered with this phone number.")

    # Admin 2FA (FRS AC-11): OTP AND gov/police ID required.
    if user.role == UserRole.ADMIN:
        supplied = payload.police_id or ""
        if not supplied or not secrets.compare_digest(supplied, _DEMO_ADMIN_POLICE_ID):
            raise HTTPException(
                status_code=401,
                detail="Administrator sign-in requires a valid police identification number.",
            )

    token, expires_in = create_access_token(str(user.id), user.role)

    audit_service.write_audit(
        db,
        action="auth.verify_otp",
        actor_id=user.id,
        model_version=None,
        prompt_version=None,
        input_data={"phone": payload.phone, "role": user.role},
        output_data={"user_id": str(user.id), "expires_in": expires_in},
    )
    db.commit()

    return VerifyOtpResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut(
            id=str(user.id),
            name=user.name,
            phone=user.phone,
            location=user.location,
            role=user.role,
        ),
    )
