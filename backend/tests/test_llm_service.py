from __future__ import annotations

from app.services import llm_service
from app.services.ai_common import ProviderUnavailableError


def test_mock_case_summary(session):
    out = llm_service.generate_case_summary(
        {"case_id": "KHJ-2024-00001", "person_name": "X", "last_seen_location": "Ahmedabad", "year_missing": 2010},
        session=session,
    )
    assert out["provider"] == "template"
    assert "KHJ-2024-00001" in out["text"]


def test_mock_family_alert_never_claims_certainty(session):
    out = llm_service.generate_family_alert(
        {"case_id": "KHJ-2024-00001", "person_name": "X"},
        {"confidence": 0.9},
        session=session,
    )
    lowered = out["text"].lower()
    assert "verify" in lowered
    assert "not a confirmation" in lowered


def test_audit_entry_written_for_each_call(session):
    llm_service.generate_case_summary(
        {"case_id": "KHJ-2024-00001", "person_name": "X", "last_seen_location": "Ahmedabad"},
        session=session,
    )
    session.flush()

    from app.models import AuditLog

    audits = session.query(AuditLog).filter(AuditLog.action == "llm.case_summary").all()
    assert len(audits) == 1
    assert audits[0].model_version == "mock-v1"  # mock mode


def test_fallback_openai_to_groq(real_mode, monkeypatch, fast_retries, session):
    def openai_fail(kind, payload):
        raise ProviderUnavailableError("openai dead")

    def groq_ok(kind, payload):
        return {"text": "Groq template response.", "tokens_used": 42, "model_version": "llama-3.3-70b-versatile"}

    monkeypatch.setattr(llm_service, "_call_openai", openai_fail)
    monkeypatch.setattr(llm_service, "_call_groq", groq_ok)

    out = llm_service.generate_case_summary({"case_id": "KHJ-2024-00001", "person_name": "X"}, session=session)
    assert out["provider"] == "groq"
    assert out["model_version"].startswith("groq/")
    assert out["tokens_used"] == 42
    assert "openai" in out["errors"]


def test_fallback_all_fail_uses_template(real_mode, monkeypatch, fast_retries, session):
    def always_fail(kind, payload):
        raise ProviderUnavailableError("down")

    monkeypatch.setattr(llm_service, "_call_openai", always_fail)
    monkeypatch.setattr(llm_service, "_call_groq", always_fail)

    out = llm_service.generate_case_summary({"case_id": "KHJ-2024-00001", "person_name": "X"}, session=session)
    assert out["provider"] == "template"
    assert set(out["errors"]) == {"openai", "groq"}


def test_gpt4o_disabled_skips_openai(real_mode, monkeypatch, fast_retries, session):
    monkeypatch.setenv("GPT4O_ENABLED", "false")
    from app.config import get_settings

    get_settings.cache_clear()

    def openai_fail(*args, **kwargs):
        raise AssertionError("OpenAI should not have been called")

    def groq_ok(kind, payload):
        return {"text": "OK", "tokens_used": 10, "model_version": "llama-3.3-70b-versatile"}

    monkeypatch.setattr(llm_service, "_call_openai", openai_fail)
    monkeypatch.setattr(llm_service, "_call_groq", groq_ok)

    out = llm_service.generate_case_summary({"case_id": "KHJ-2024-00001", "person_name": "X"}, session=session)
    assert out["provider"] == "groq"
