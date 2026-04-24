from __future__ import annotations

from app.models import AppSettings
from app.services import scoring_service


def _set(session, key, value):
    session.add(AppSettings(key=key, value=value))
    session.flush()


def test_defaults_when_settings_missing(session):
    high = scoring_service.compute_confidence(session, similarity_score=0.7)   # conf=0.85
    assert high["tier"] == "high"
    assert high["action"] == "auto_alert_field_worker"

    mid = scoring_service.compute_confidence(session, similarity_score=0.3)    # conf=0.65
    assert mid["tier"] == "medium"
    assert mid["action"] == "queue_for_human_review"

    low = scoring_service.compute_confidence(session, similarity_score=-0.2)   # conf=0.40
    assert low["tier"] == "low"
    assert low["action"] == "mark_inconclusive"


def test_boundary_values(session):
    # sim=0.6 → confidence 0.80 → exactly the auto-alert threshold
    result = scoring_service.compute_confidence(session, 0.6)
    assert result["score"] == 0.8
    assert result["tier"] == "high"

    # sim=0.2 → confidence 0.60 → exactly the review threshold
    result = scoring_service.compute_confidence(session, 0.2)
    assert result["score"] == 0.6
    assert result["tier"] == "medium"


def test_custom_thresholds_from_app_settings(session):
    _set(session, "confidence_threshold", 0.50)
    _set(session, "auto_alert_threshold", 0.90)

    mid = scoring_service.compute_confidence(session, similarity_score=0.7)  # conf=0.85
    assert mid["tier"] == "medium"  # below the raised auto-alert threshold now

    high = scoring_service.compute_confidence(session, 0.85)  # conf=0.925
    assert high["tier"] == "high"
