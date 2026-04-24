"""Deterministic mocks for every AI service.

Activated by ``USE_MOCK_AI=true``. Every mock output is seeded from the SHA-256
of its inputs, so repeated calls return identical results — this is what lets
pytest assert concrete values without baking real models into the repo.
"""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

MOCK_MODEL_VERSION = "mock-v1"
MOCK_PROMPT_VERSION = "mock-prompt-v1"


def _seed_from(data: Any) -> int:
    if isinstance(data, bytes):
        payload = data
    elif isinstance(data, str):
        payload = data.encode("utf-8")
    else:
        payload = repr(data).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def mock_embedding(data: Any) -> np.ndarray:
    """Return a deterministic 512-d L2-normalised vector seeded from ``data``."""
    rng = np.random.default_rng(_seed_from(data))
    vec = rng.standard_normal(512)
    return (vec / (np.linalg.norm(vec) or 1.0)).astype(np.float64)


def mock_detect_face(image_bytes_or_url: bytes | str) -> dict:
    seed = _seed_from(image_bytes_or_url)
    rng = np.random.default_rng(seed)
    # Plausible bbox + 68-point landmark map.
    landmarks = rng.uniform(0, 224, size=(68, 2)).tolist()
    return {
        "bbox": [48.0, 48.0, 176.0, 176.0],
        "landmarks_68": landmarks,
        "confidence": 0.99,
        "face_img_bytes": b"MOCK_FACE::" + (image_bytes_or_url if isinstance(image_bytes_or_url, bytes) else image_bytes_or_url.encode()),
    }


def mock_aged_url(target_age: int) -> str:
    return f"https://placehold.co/512x512?text=Aged+to+{target_age}"


def mock_aging_result(target_age: int) -> dict:
    return {
        "url": mock_aged_url(target_age),
        "provider": "mock",
        "aging_unavailable": True,
        "model_version": MOCK_MODEL_VERSION,
    }


def mock_llm_response(kind: str, payload: dict) -> dict:
    """Return a deterministic template-style response."""
    seed = _seed_from((kind, payload))
    tokens = 40 + (seed % 60)
    return {
        "text": _mock_text(kind, payload),
        "provider": "template",
        "model_version": MOCK_MODEL_VERSION,
        "prompt_version": MOCK_PROMPT_VERSION,
        "tokens_used": tokens,
    }


def _mock_text(kind: str, payload: dict) -> str:
    name = payload.get("person_name", "the missing person")
    case_id = payload.get("case_id", "KHJ-XXXX-XXXXX")
    if kind == "case_summary":
        return (
            f"Case {case_id} concerns {name}, last seen in "
            f"{payload.get('last_seen_location', 'an unknown location')} in "
            f"{payload.get('year_missing', 'an unknown year')}. "
            "AI-generated content for investigator review only."
        )
    if kind == "family_alert":
        return (
            f"Hello, regarding {name} (Case {case_id}): a possible sighting has "
            "been recorded. A certified officer will verify this before any "
            "further action is taken. This is not a confirmation."
        )
    if kind == "match_sighting":
        return (
            f"Candidate sighting compared against {name}'s aged profile. "
            "Similarity warrants field verification per KHOJO protocol."
        )
    return "Template response."
