"""Confidence scoring and tier routing (FRS FR-3.6, FR-3.7, FR-4.3).

The cosine similarity returned by ``recognition_service`` lies in ``[-1, 1]``.
We map it to the standard ``[0, 1]`` confidence range with a clipped
sigmoid-like transform and then bucket into the three tiers:

    score ≥ auto_alert_threshold          → "high"   (auto_alert_field_worker)
    confidence_threshold ≤ score < auto   → "medium" (queue_for_human_review)
    score < confidence_threshold          → "low"    (mark_inconclusive)

Thresholds are loaded from ``app_settings`` at call time so admin-console
changes take effect on the next request (FRS §6.6 Tab 4 / §7.6.4).
"""
from __future__ import annotations

import logging
from typing import TypedDict

from sqlalchemy.orm import Session

from app.models import AppSettings

logger = logging.getLogger(__name__)

# Fallback defaults (also what the seed script writes into app_settings).
DEFAULT_CONFIDENCE_THRESHOLD = 0.60
DEFAULT_AUTO_ALERT_THRESHOLD = 0.80


class ScoreResult(TypedDict):
    score: float
    tier: str
    action: str


def _load_threshold(session: Session, key: str, default: float) -> float:
    row = session.get(AppSettings, key)
    if row is None or row.value is None:
        return default
    try:
        return float(row.value)
    except (TypeError, ValueError):
        logger.warning("app_settings[%s]=%r is not numeric; using default %s", key, row.value, default)
        return default


def _cosine_to_confidence(similarity: float) -> float:
    """Map cosine similarity (-1..1) to [0, 1] confidence, clipped at the edges.

    ArcFace embeddings are L2-normalised so cosine similarity of identity
    matches sits roughly in [0.5, 1.0]. A plain ``(1 + sim) / 2`` mapping
    preserves the ordering and gives us a human-readable score.
    """
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def compute_confidence(
    session: Session,
    similarity_score: float,
) -> ScoreResult:
    confidence = _cosine_to_confidence(similarity_score)
    confidence_threshold = _load_threshold(
        session, "confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD
    )
    auto_alert_threshold = _load_threshold(
        session, "auto_alert_threshold", DEFAULT_AUTO_ALERT_THRESHOLD
    )

    if confidence >= auto_alert_threshold:
        tier, action = "high", "auto_alert_field_worker"
    elif confidence >= confidence_threshold:
        tier, action = "medium", "queue_for_human_review"
    else:
        tier, action = "low", "mark_inconclusive"

    return ScoreResult(score=float(confidence), tier=tier, action=action)
