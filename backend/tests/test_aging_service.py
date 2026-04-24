from __future__ import annotations

import pytest

from app.services import aging_service
from app.services.ai_common import ProviderUnavailableError


def test_mock_mode_returns_placeholder():
    result = aging_service.age_progress(b"face", target_age=27, case_id="KHJ-2024-00001")
    assert result["provider"] == "mock"
    assert result["aging_unavailable"] is True
    assert "Aged+to+27" in result["url"]


def test_fallback_chain_hf_fails_colab_succeeds(real_mode, monkeypatch, fast_retries):
    def hf_fail(image_bytes, target_age):
        raise ProviderUnavailableError("HF down")

    def colab_ok(image_bytes, target_age):
        return b"PNG_BYTES"

    def fake_upload(image_bytes, case_id, target_age):
        return f"https://fake.supabase/{case_id}/aged_{target_age}.png"

    monkeypatch.setattr(aging_service, "_call_hf", hf_fail)
    monkeypatch.setattr(aging_service, "_call_colab", colab_ok)
    monkeypatch.setattr(aging_service, "_upload_to_supabase", fake_upload)

    result = aging_service.age_progress(b"face", target_age=27, case_id="KHJ-2024-00001")
    assert result["provider"] == "colab"
    assert result["aging_unavailable"] is False
    assert result["url"].endswith("/aged_27.png")
    assert "huggingface" in result["errors"]


def test_fallback_chain_all_fail_returns_mock(real_mode, monkeypatch, fast_retries):
    def always_fail(image_bytes, target_age):
        raise ProviderUnavailableError("down")

    monkeypatch.setattr(aging_service, "_call_hf", always_fail)
    monkeypatch.setattr(aging_service, "_call_colab", always_fail)
    monkeypatch.setattr(aging_service, "_upload_to_supabase", lambda *a, **k: pytest.fail("unreachable"))

    result = aging_service.age_progress(b"face", target_age=27, case_id="KHJ-2024-00001")
    assert result["provider"] == "mock"
    assert result["aging_unavailable"] is True
    assert set(result["errors"]) == {"huggingface", "colab"}


def test_circuit_breaker_opens_after_five_failures(real_mode, monkeypatch, fast_retries):
    call_count = {"n": 0}

    def hf_fail(image_bytes, target_age):
        call_count["n"] += 1
        raise ProviderUnavailableError("boom")

    monkeypatch.setattr(aging_service, "_call_hf", hf_fail)
    # Colab absent => pure mock fallthrough.
    monkeypatch.setattr(aging_service, "_call_colab", lambda *a, **k: (_ for _ in ()).throw(ProviderUnavailableError("no colab")))
    monkeypatch.setattr(aging_service, "_upload_to_supabase", lambda *a, **k: "unused")

    # Invoke 6 times — after 5 failures the HF breaker should open and subsequent
    # calls should short-circuit without calling _call_hf.
    for _ in range(6):
        aging_service.age_progress(b"x", 27, "KHJ-2024-00001")

    assert aging_service._HF_BREAKER.is_open()
    # With RETRY_ATTEMPTS=2, each of the first 5 invocations calls _call_hf 2x
    # (5 × 2 = 10). After the breaker opens invocations should short-circuit.
    assert call_count["n"] == 10
