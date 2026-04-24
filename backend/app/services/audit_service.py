"""Tamper-evident audit log service (FRS §10.3, AL-3, AL-4).

Every AI decision is hashed (SHA-256 over a canonical JSON form of the
input/output payload) and signed (HMAC-SHA256 with ``AUDIT_SIGNING_SECRET``).
The resulting row is append-only — updates and deletes are blocked at the
model layer (see ``app.models.audit_log``).
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Keys that must never leak into the hash input.
_PII_KEYS = {
    "phone",
    "phone_number",
    "mobile",
    "otp",
    "otp_code",
    "password",
    "gov_id",
    "government_id",
    "photo_url",
    "supabase_url",
    "real_photo_url",
}

# 10–15 digit runs with optional + prefix — covers Indian and international numbers.
_PHONE_PATTERN = re.compile(r"\+?\d[\d\- ]{9,14}\d")
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

_REDACTED = "[REDACTED]"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (_REDACTED if k.lower() in _PII_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str):
        if _URL_PATTERN.search(value):
            return _REDACTED
        if _PHONE_PATTERN.fullmatch(value.strip()):
            return _REDACTED
        return value
    return value


def _canonical_json(payload: Any) -> str:
    return json.dumps(_redact(payload), sort_keys=True, separators=(",", ":"), default=str)


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _row_signable(
    *,
    timestamp: datetime,
    actor_id: uuid.UUID | None,
    action: str,
    model_version: str | None,
    prompt_version: str | None,
    input_hash: str,
    output_hash: str,
    confidence_score: float | None,
    tokens_used: int | None,
) -> str:
    return json.dumps(
        {
            "timestamp": timestamp.astimezone(timezone.utc).isoformat(),
            "actor_id": str(actor_id) if actor_id else None,
            "action": action,
            "model_version": model_version,
            "prompt_version": prompt_version,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "confidence_score": confidence_score,
            "tokens_used": tokens_used,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _hmac(signable: str, secret: str | None = None) -> str:
    key = (secret or get_settings().audit_signing_secret).encode("utf-8")
    return hmac.new(key, signable.encode("utf-8"), hashlib.sha256).hexdigest()


def write_audit(
    session: Session,
    *,
    action: str,
    actor_id: uuid.UUID | None,
    model_version: str | None,
    prompt_version: str | None,
    input_data: Any,
    output_data: Any,
    confidence_score: float | None = None,
    tokens_used: int | None = None,
) -> AuditLog:
    """Insert an append-only audit row. Returns the persisted row."""
    ts = datetime.now(timezone.utc)
    input_hash = _sha256(input_data)
    output_hash = _sha256(output_data)
    signable = _row_signable(
        timestamp=ts,
        actor_id=actor_id,
        action=action,
        model_version=model_version,
        prompt_version=prompt_version,
        input_hash=input_hash,
        output_hash=output_hash,
        confidence_score=confidence_score,
        tokens_used=tokens_used,
    )
    row = AuditLog(
        timestamp=ts,
        actor_id=actor_id,
        action=action,
        model_version=model_version,
        prompt_version=prompt_version,
        input_hash=input_hash,
        output_hash=output_hash,
        confidence_score=confidence_score,
        tokens_used=tokens_used,
        hmac_signature=_hmac(signable),
    )
    session.add(row)
    session.flush()
    logger.info("audit append id=%s action=%s", row.id, action)
    return row


def _row_signature(row: AuditLog) -> str:
    signable = _row_signable(
        timestamp=row.timestamp,
        actor_id=row.actor_id,
        action=row.action,
        model_version=row.model_version,
        prompt_version=row.prompt_version,
        input_hash=row.input_hash,
        output_hash=row.output_hash,
        confidence_score=row.confidence_score,
        tokens_used=row.tokens_used,
    )
    return _hmac(signable)


def verify_audit_chain(
    session: Session,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> bool:
    """Recompute every row's HMAC in the range; True iff all match."""
    stmt = select(AuditLog).order_by(AuditLog.id)
    if from_date is not None:
        stmt = stmt.where(AuditLog.timestamp >= from_date)
    if to_date is not None:
        stmt = stmt.where(AuditLog.timestamp <= to_date)

    for row in session.execute(stmt).scalars():
        if not hmac.compare_digest(_row_signature(row), row.hmac_signature):
            logger.warning("audit tampering detected at id=%s", row.id)
            return False
    return True


def export_audit_csv(
    session: Session,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> str:
    """Return a CSV dump of the audit log in the range, with PII redacted."""
    stmt = select(AuditLog).order_by(AuditLog.id)
    if from_date is not None:
        stmt = stmt.where(AuditLog.timestamp >= from_date)
    if to_date is not None:
        stmt = stmt.where(AuditLog.timestamp <= to_date)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "timestamp",
            "actor_id",
            "action",
            "model_version",
            "prompt_version",
            "input_hash",
            "output_hash",
            "confidence_score",
            "tokens_used",
            "hmac_signature",
        ]
    )
    for row in session.execute(stmt).scalars():
        writer.writerow(
            [
                row.id,
                row.timestamp.isoformat() if row.timestamp else "",
                str(row.actor_id) if row.actor_id else "",
                row.action,
                row.model_version or "",
                row.prompt_version or "",
                row.input_hash,
                row.output_hash,
                "" if row.confidence_score is None else f"{row.confidence_score:.6f}",
                "" if row.tokens_used is None else row.tokens_used,
                row.hmac_signature,
            ]
        )
    return buf.getvalue()
