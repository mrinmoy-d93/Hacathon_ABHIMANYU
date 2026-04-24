"""Face-aging service with a three-tier free-tier fallback chain.

    primary   — Hugging Face Inference API (huggingface_hub.InferenceClient)
    secondary — Self-hosted Colab + ngrok endpoint (COLAB_AGING_URL)
    tertiary  — Deterministic mock (always succeeds, flags aging_unavailable=True)

Each provider is guarded by:

* Retry with exponential backoff (tenacity, 3 attempts, 0.5→4.0 s).
* A per-provider :class:`CircuitBreaker` (5 consecutive failures → 60 s
  cooldown, FRS NFR-5).

On success the generated image is re-uploaded to the Supabase ``case-photos``
bucket so downstream services see a single canonical URL. See
``docs/AGING_PROVIDERS.md`` for operator setup per provider.
"""
from __future__ import annotations

import logging
from typing import Callable

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.services._mock_ai import mock_aging_result
from app.services.ai_common import (
    AllProvidersFailedError,
    CircuitBreaker,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Module-level breakers so multiple calls share failure state.
_HF_BREAKER = CircuitBreaker("aging.huggingface")
_COLAB_BREAKER = CircuitBreaker("aging.colab")

# tenacity retry config (3 attempts, 0.5→4s exponential) — exposed as module
# attributes so tests can monkey-patch them to zero.
RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN = 0.5
RETRY_WAIT_MAX = 4.0


def _retrying(fn: Callable[..., bytes]) -> Callable[..., bytes]:
    """Wrap ``fn`` with tenacity retry-on-provider-failure."""
    return retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=RETRY_WAIT_MIN, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception_type((ProviderUnavailableError, httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )(fn)


def _call_hf(image_bytes: bytes, target_age: int) -> bytes:
    settings = get_settings()
    if not settings.hf_token:
        raise ProviderUnavailableError("HF_TOKEN is not configured")

    try:
        from huggingface_hub import InferenceClient  # local import — keeps tests portable
    except ImportError as exc:  # pragma: no cover
        raise ProviderUnavailableError("huggingface_hub is not installed") from exc

    client = InferenceClient(token=settings.hf_token, timeout=30)
    try:
        result = client.post(
            data=image_bytes,
            model=settings.hf_aging_model,
            json={"parameters": {"target_age": int(target_age)}},
        )
    except Exception as exc:  # noqa: BLE001 — convert any HF-SDK error
        raise ProviderUnavailableError(f"Hugging Face inference failed: {exc}") from exc

    if isinstance(result, (bytes, bytearray, memoryview)):
        return bytes(result)
    raise ProviderUnavailableError(f"unexpected Hugging Face response type: {type(result).__name__}")


def _call_colab(image_bytes: bytes, target_age: int) -> bytes:
    settings = get_settings()
    if not settings.colab_aging_url:
        raise ProviderUnavailableError("COLAB_AGING_URL is not configured")

    with httpx.Client(timeout=30.0) as client:
        try:
            resp = client.post(
                settings.colab_aging_url,
                files={"image": ("face.png", image_bytes, "image/png")},
                data={"target_age": str(int(target_age))},
            )
        except (httpx.TransportError, httpx.TimeoutException):
            raise
        if resp.status_code >= 400:
            raise ProviderUnavailableError(f"Colab returned HTTP {resp.status_code}")
        return resp.content


def _upload_to_supabase(image_bytes: bytes, case_id: str, target_age: int) -> str:
    """Re-upload a generated aged face to the case-photos bucket."""
    from app.services import supabase_service  # local import — avoids cycles

    settings = get_settings()
    return supabase_service.upload_photo(
        file_bytes=image_bytes,
        bucket=settings.supabase_bucket_case_photos,
        case_id=case_id,
        filename=f"aged_{int(target_age)}.png",
        content_type="image/png",
    )


def _try_provider(name: str, breaker: CircuitBreaker, fn: Callable[..., bytes], *args) -> bytes:
    if breaker.is_open():
        raise ProviderUnavailableError(f"{name} circuit breaker is open")
    try:
        result = _retrying(fn)(*args)
    except (ProviderUnavailableError, RetryError, httpx.TransportError, httpx.TimeoutException) as exc:
        breaker.record_failure()
        raise ProviderUnavailableError(f"{name} failed: {exc}") from exc
    breaker.record_success()
    return result


def age_progress(
    image_bytes: bytes,
    target_age: int,
    case_id: str,
) -> dict:
    """Generate an aged face at ``target_age``. Falls through providers on failure.

    Returns a dict::

        {
            "url": str,                 # public URL of the aged image
            "provider": "huggingface" | "colab" | "mock",
            "aging_unavailable": bool,  # True only for mock
            "model_version": str,
            "errors": {provider: str, ...},  # diagnostic context
        }
    """
    settings = get_settings()

    if settings.use_mock_ai:
        return {**mock_aging_result(target_age), "errors": {}}

    errors: dict[str, str] = {}

    # 1. Hugging Face Inference API
    try:
        aged_bytes = _try_provider("huggingface", _HF_BREAKER, _call_hf, image_bytes, target_age)
        url = _upload_to_supabase(aged_bytes, case_id, target_age)
        return {
            "url": url,
            "provider": "huggingface",
            "aging_unavailable": False,
            "model_version": settings.hf_aging_model,
            "errors": errors,
        }
    except ProviderUnavailableError as exc:
        errors["huggingface"] = str(exc)
        logger.warning("aging.huggingface unavailable: %s", exc)

    # 2. Colab + ngrok
    try:
        aged_bytes = _try_provider("colab", _COLAB_BREAKER, _call_colab, image_bytes, target_age)
        url = _upload_to_supabase(aged_bytes, case_id, target_age)
        return {
            "url": url,
            "provider": "colab",
            "aging_unavailable": False,
            "model_version": "colab-aging",
            "errors": errors,
        }
    except ProviderUnavailableError as exc:
        errors["colab"] = str(exc)
        logger.warning("aging.colab unavailable: %s", exc)

    # 3. Mock — always succeeds. Flags aging_unavailable so the UI can explain why.
    logger.warning("all aging providers failed, falling back to mock: %s", errors)
    result = mock_aging_result(target_age)
    return {**result, "errors": errors}


def raise_if_all_fail(result: dict) -> None:
    """Optional helper used by tests that want a hard failure instead of mock."""
    if result.get("provider") == "mock" and result.get("errors"):
        raise AllProvidersFailedError(f"all aging providers failed: {result['errors']}")
