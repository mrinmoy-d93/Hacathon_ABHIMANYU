"""LLM service with three-tier free-tier fallback chain.

    primary   — OpenAI GPT-4o (OPENAI_API_KEY, hackathon-provided credits)
    secondary — Groq Llama 3.3 70B (GROQ_API_KEY, free tier, OpenAI-compatible)
    tertiary  — Deterministic templates (always succeeds)

Public surface:

* :func:`generate_case_summary` — investigator-oriented case digest.
* :func:`generate_family_alert` — never claims certainty; always includes
  "a certified officer will verify" (FRS FR-4.4).
* :func:`match_sighting_to_profile` — natural-language explanation of why a
  sighting was flagged against a missing-person profile.

Every call writes an audit entry via :mod:`app.services.audit_service` with
``model_version=<provider>/<model>`` and the actual ``tokens_used``.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Callable

from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.services import audit_service
from app.services._mock_ai import mock_llm_response
from app.services.ai_common import CircuitBreaker, ProviderUnavailableError

logger = logging.getLogger(__name__)

_OPENAI_BREAKER = CircuitBreaker("llm.openai")
_GROQ_BREAKER = CircuitBreaker("llm.groq")

RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN = 0.5
RETRY_WAIT_MAX = 4.0

MAX_TOKENS = 300
TEMPERATURE = 0.3

_SYSTEM_PROMPTS = {
    "case_summary": (
        "You are an assistant to investigators working on missing-person cases. "
        "Write a concise, factual case summary in plain English. Do NOT speculate "
        "about the outcome. Do NOT claim certainty about any match."
    ),
    "family_alert": (
        "You are a caring but careful communicator for a missing-persons programme. "
        "Write a message to the registered family. Never state that a match is "
        "confirmed; always note that a certified officer will verify before any "
        "further action is taken."
    ),
    "match_sighting": (
        "You are an investigator assistant. Describe why a sighting was flagged "
        "against a missing-person profile, citing the available facts only. "
        "Never claim identity certainty."
    ),
}


# ─── retry wrapper ────────────────────────────────────────────────────────
def _retrying(fn: Callable[..., dict]) -> Callable[..., dict]:
    return retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=RETRY_WAIT_MIN, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception_type(ProviderUnavailableError),
        reraise=True,
    )(fn)


# ─── providers ────────────────────────────────────────────────────────────
def _render_system_prompt(kind: str, prompt_version: str) -> str:
    base = _SYSTEM_PROMPTS.get(kind, "")
    return f"[prompt_version:{prompt_version}]\n{base}"


def _call_openai_compat(api_key: str, base_url: str | None, model: str, kind: str, payload: dict) -> dict:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise ProviderUnavailableError("openai SDK is not installed") from exc

    settings = get_settings()
    try:
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": _render_system_prompt(kind, settings.openai_prompt_version)},
                {"role": "user", "content": _user_prompt(kind, payload)},
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise ProviderUnavailableError(f"LLM call failed: {exc}") from exc

    choice = resp.choices[0]
    text = (choice.message.content or "").strip()
    usage = getattr(resp, "usage", None)
    tokens = getattr(usage, "total_tokens", None) if usage else None
    return {"text": text, "tokens_used": tokens, "model_version": model}


def _call_openai(kind: str, payload: dict) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ProviderUnavailableError("OPENAI_API_KEY not set")
    return _call_openai_compat(
        api_key=settings.openai_api_key,
        base_url=None,
        model=settings.openai_model,
        kind=kind,
        payload=payload,
    )


def _call_groq(kind: str, payload: dict) -> dict:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ProviderUnavailableError("GROQ_API_KEY not set")
    return _call_openai_compat(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        model=settings.groq_model,
        kind=kind,
        payload=payload,
    )


def _user_prompt(kind: str, payload: dict) -> str:
    # Keep the user prompt compact so max_tokens=300 is enough for a summary.
    if kind == "case_summary":
        return (
            f"Case ID: {payload.get('case_id')}\n"
            f"Person: {payload.get('person_name')}\n"
            f"Year missing: {payload.get('year_missing')}\n"
            f"Age at disappearance: {payload.get('age_at_disappearance')}\n"
            f"Last seen: {payload.get('last_seen_location')}\n"
            f"Identifying marks: {payload.get('identifying_marks') or 'none recorded'}\n\n"
            "Write a 3–5 sentence case summary for an investigator."
        )
    if kind == "family_alert":
        return (
            f"Case ID: {payload.get('case_id')}\n"
            f"Person: {payload.get('person_name')}\n"
            f"Confidence: {payload.get('confidence_score')}\n"
            f"Tier: {payload.get('tier')}\n\n"
            "Write a 2–4 sentence message to the family. Never claim certainty."
        )
    if kind == "match_sighting":
        return (
            f"Case ID: {payload.get('case_id')}\n"
            f"Sighting location: {payload.get('sighting_location')}\n"
            f"Confidence: {payload.get('confidence_score')}\n\n"
            "Describe, in 2–3 sentences, why this sighting was flagged for review."
        )
    return str(payload)


# ─── fallback chain ───────────────────────────────────────────────────────
def _try_provider(name: str, breaker: CircuitBreaker, fn: Callable[..., dict], kind: str, payload: dict) -> dict:
    if breaker.is_open():
        raise ProviderUnavailableError(f"{name} circuit breaker is open")
    try:
        result = _retrying(fn)(kind, payload)
    except ProviderUnavailableError:
        breaker.record_failure()
        raise
    breaker.record_success()
    return result


def _call_with_fallback(kind: str, payload: dict) -> dict:
    settings = get_settings()
    prompt_version = settings.openai_prompt_version
    errors: dict[str, str] = {}

    if settings.gpt4o_enabled:
        try:
            out = _try_provider("openai", _OPENAI_BREAKER, _call_openai, kind, payload)
            return {
                "text": out["text"],
                "provider": "openai",
                "model_version": f"openai/{out.get('model_version', settings.openai_model)}",
                "prompt_version": prompt_version,
                "tokens_used": out.get("tokens_used"),
                "errors": errors,
            }
        except ProviderUnavailableError as exc:
            errors["openai"] = str(exc)
            logger.warning("llm.openai unavailable: %s", exc)

    try:
        out = _try_provider("groq", _GROQ_BREAKER, _call_groq, kind, payload)
        return {
            "text": out["text"],
            "provider": "groq",
            "model_version": f"groq/{out.get('model_version', settings.groq_model)}",
            "prompt_version": prompt_version,
            "tokens_used": out.get("tokens_used"),
            "errors": errors,
        }
    except ProviderUnavailableError as exc:
        errors["groq"] = str(exc)
        logger.warning("llm.groq unavailable: %s", exc)

    logger.warning("all LLM providers failed — falling back to template: %s", errors)
    template = mock_llm_response(kind, payload)
    return {**template, "errors": errors}


# ─── public API ───────────────────────────────────────────────────────────
def _invoke(
    kind: str,
    payload: dict,
    *,
    session: Session | None,
    actor_id: uuid.UUID | None,
) -> dict:
    settings = get_settings()

    if settings.use_mock_ai:
        result = mock_llm_response(kind, payload)
        result["errors"] = {}
    else:
        result = _call_with_fallback(kind, payload)

    if session is not None:
        audit_service.write_audit(
            session,
            action=f"llm.{kind}",
            actor_id=actor_id,
            model_version=result["model_version"],
            prompt_version=result.get("prompt_version"),
            input_data={"kind": kind, "payload": payload},
            output_data={"text_preview": result["text"][:120], "provider": result["provider"]},
            tokens_used=result.get("tokens_used"),
        )
    return result


def generate_case_summary(case: dict, *, session: Session | None = None, actor_id: uuid.UUID | None = None) -> dict:
    return _invoke("case_summary", case, session=session, actor_id=actor_id)


def generate_family_alert(
    case: dict, match: dict, *, session: Session | None = None, actor_id: uuid.UUID | None = None
) -> dict:
    payload = {**case, **match}
    return _invoke("family_alert", payload, session=session, actor_id=actor_id)


def match_sighting_to_profile(
    case: dict, sighting: dict, *, session: Session | None = None, actor_id: uuid.UUID | None = None
) -> dict:
    payload = {**case, **sighting}
    return _invoke("match_sighting", payload, session=session, actor_id=actor_id)


# Expose provider entry points for pytest monkeypatching.
__all__ = [
    "generate_case_summary",
    "generate_family_alert",
    "match_sighting_to_profile",
    "_call_openai",
    "_call_groq",
    "_OPENAI_BREAKER",
    "_GROQ_BREAKER",
]
