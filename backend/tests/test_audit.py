from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from app.models import AuditLog
from app.services import audit_service, supabase_service


def test_write_audit_inserts_row_with_hashes(session):
    row = audit_service.write_audit(
        session,
        action="ai.infer",
        actor_id=None,
        model_version="v1.0",
        prompt_version=None,
        input_data={"case_id": "KHJ-2024-00001"},
        output_data={"score": 0.87},
        confidence_score=0.87,
        tokens_used=42,
    )
    session.commit()

    assert row.id is not None
    assert len(row.input_hash) == 64
    assert len(row.output_hash) == 64
    assert len(row.hmac_signature) == 64


def test_write_audit_redacts_pii_from_hash(session):
    row_with_phone = audit_service.write_audit(
        session,
        action="auth.otp.send",
        actor_id=None,
        model_version=None,
        prompt_version=None,
        input_data={"phone": "+919812300001"},
        output_data={"sent": True},
    )
    row_with_redacted = audit_service.write_audit(
        session,
        action="auth.otp.send",
        actor_id=None,
        model_version=None,
        prompt_version=None,
        input_data={"phone": "[REDACTED]"},
        output_data={"sent": True},
    )
    session.commit()
    # Redacted-at-source input must produce the same hash as the live call
    # that relied on the PII redactor — proving PII never reaches the hash.
    assert row_with_phone.input_hash == row_with_redacted.input_hash


def test_verify_audit_chain_returns_true_when_intact(session):
    for i in range(3):
        audit_service.write_audit(
            session,
            action=f"ai.infer.{i}",
            actor_id=None,
            model_version="v1.0",
            prompt_version=None,
            input_data={"i": i},
            output_data={"i": i},
        )
    session.commit()
    assert audit_service.verify_audit_chain(session) is True


def test_verify_audit_chain_detects_raw_sql_tampering(session):
    row = audit_service.write_audit(
        session,
        action="ai.infer",
        actor_id=None,
        model_version="v1.0",
        prompt_version=None,
        input_data={"case_id": "KHJ-2024-00001"},
        output_data={"score": 0.5},
        confidence_score=0.5,
    )
    session.commit()

    # Bypass the ORM's before_flush guard with raw SQL to simulate an attacker
    # with direct DB access.
    session.execute(
        text("UPDATE audit_log SET confidence_score = 0.99 WHERE id = :id"),
        {"id": row.id},
    )
    session.commit()
    session.expire_all()

    assert audit_service.verify_audit_chain(session) is False


def test_export_audit_csv_contains_header_and_rows(session):
    audit_service.write_audit(
        session,
        action="ai.infer",
        actor_id=None,
        model_version="v1.0",
        prompt_version=None,
        input_data={"x": 1},
        output_data={"y": 2},
        confidence_score=0.75,
        tokens_used=100,
    )
    session.commit()

    now = datetime.now(timezone.utc)
    csv_text = audit_service.export_audit_csv(
        session, from_date=now - timedelta(minutes=1), to_date=now + timedelta(minutes=1)
    )
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("id,timestamp,actor_id,action,model_version")
    assert len(lines) == 2
    assert "ai.infer" in lines[1]


def test_supabase_upload_photo_mocked(monkeypatch):
    fake_client = MagicMock()
    fake_bucket = MagicMock()
    fake_client.storage.from_.return_value = fake_bucket
    fake_bucket.get_public_url.return_value = (
        "https://test.supabase.co/storage/v1/object/public/case-photos/KHJ-2024-00001/abc.jpg"
    )
    # Replace both the cached client and the factory.
    supabase_service.get_client.cache_clear()
    monkeypatch.setattr(supabase_service, "get_client", lambda: fake_client)

    url = supabase_service.upload_photo(
        b"fakedata", "case-photos", "KHJ-2024-00001", filename="photo.jpg"
    )

    assert "case-photos" in url
    fake_client.storage.from_.assert_called_with("case-photos")
    fake_bucket.upload.assert_called_once()
    call_kwargs = fake_bucket.upload.call_args.kwargs
    assert call_kwargs["path"].startswith("KHJ-2024-00001/")
    assert call_kwargs["path"].endswith(".jpg")
    assert call_kwargs["file"] == b"fakedata"


def test_supabase_delete_photo_mocked(monkeypatch):
    fake_client = MagicMock()
    fake_bucket = MagicMock()
    fake_client.storage.from_.return_value = fake_bucket
    supabase_service.get_client.cache_clear()
    monkeypatch.setattr(supabase_service, "get_client", lambda: fake_client)

    supabase_service.delete_photo(
        "https://test.supabase.co/storage/v1/object/public/case-photos/KHJ-2024-00001/abc.jpg"
    )

    fake_client.storage.from_.assert_called_with("case-photos")
    fake_bucket.remove.assert_called_once_with(["KHJ-2024-00001/abc.jpg"])


def test_supabase_delete_photo_rejects_bad_url(monkeypatch):
    fake_client = MagicMock()
    supabase_service.get_client.cache_clear()
    monkeypatch.setattr(supabase_service, "get_client", lambda: fake_client)

    with pytest.raises(ValueError):
        supabase_service.delete_photo("https://example.com/not-supabase")


def test_audit_log_count(session):
    audit_service.write_audit(
        session,
        action="ai.infer",
        actor_id=None,
        model_version="v1.0",
        prompt_version=None,
        input_data={"x": 1},
        output_data={"y": 2},
    )
    session.commit()
    count = session.query(AuditLog).count()
    assert count == 1
