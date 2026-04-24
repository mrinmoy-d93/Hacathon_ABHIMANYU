from __future__ import annotations

import uuid

from app.models import Case, CaseStatus, Match, MatchStatus, Photo, User, UserRole
from app.services import alert_router


def _bootstrap(session, monkeypatch, case_coords=(23.03, 72.58), worker_coords=(23.05, 72.60)):
    # Mock the geocoder so tests don't hit Nominatim.
    alert_router._geocode.cache_clear()

    def _fake_geocode(location: str):
        if not location:
            return None
        if location.startswith("WORKER"):
            return worker_coords
        return case_coords

    monkeypatch.setattr(alert_router, "_geocode", _fake_geocode)

    user = User(name="creator", phone="+919811100501", location="Ahmedabad", role=UserRole.FAMILY)
    worker = User(name="worker", phone="+919811100502", location="WORKER_CITY", role=UserRole.FIELD_WORKER)
    session.add_all([user, worker])
    session.flush()

    case = Case(
        case_id="KHJ-2024-00010",
        person_name="Test",
        year_missing=2015,
        age_at_disappearance=10,
        last_seen_location="Ahmedabad",
        status=CaseStatus.ACTIVE,
        created_by=user.id,
    )
    session.add(case)
    session.flush()

    photo = Photo(
        id=uuid.uuid4(),
        case_id=case.case_id,
        supabase_url="https://fake/sighting.jpg",
        age_at_photo=15,
        embedding=[0.1] * 512,
    )
    session.add(photo)
    session.flush()
    return user, worker, case, photo


def test_high_tier_creates_match_and_assigns_worker(session, monkeypatch):
    user, worker, case, photo = _bootstrap(session, monkeypatch)

    result = alert_router.route(
        session,
        case,
        candidate_photo_id=photo.id,
        similarity_score=0.92,
        tier="high",
        actor_id=user.id,
    )
    session.flush()

    assert result["action"] == "auto_alert_field_worker"
    assert result["match_id"] is not None
    assert result["assigned_field_worker_id"] == str(worker.id)

    match = session.query(Match).one()
    assert match.status == MatchStatus.PENDING
    assert match.field_worker_id == worker.id


def test_medium_tier_creates_match_without_assignment(session, monkeypatch):
    user, worker, case, photo = _bootstrap(session, monkeypatch)

    result = alert_router.route(
        session,
        case,
        candidate_photo_id=photo.id,
        similarity_score=0.70,
        tier="medium",
        actor_id=user.id,
    )

    assert result["action"] == "queue_for_human_review"
    assert result["match_id"] is not None
    assert result["assigned_field_worker_id"] is None


def test_low_tier_skips_match_creation(session, monkeypatch):
    user, worker, case, photo = _bootstrap(session, monkeypatch)

    result = alert_router.route(
        session,
        case,
        candidate_photo_id=photo.id,
        similarity_score=0.10,
        tier="low",
        actor_id=user.id,
    )

    assert result["action"] == "mark_inconclusive"
    assert result["match_id"] is None
    assert session.query(Match).count() == 0


def test_geo_cluster_triggers_audit_event(session, monkeypatch):
    # Register three cases at the same coords within the 7-day window.
    user, worker, case1, photo = _bootstrap(session, monkeypatch)

    for i in (2, 3):
        session.add(
            Case(
                case_id=f"KHJ-2024-0002{i}",
                person_name=f"Extra {i}",
                year_missing=2018,
                age_at_disappearance=5,
                last_seen_location="Ahmedabad",
                status=CaseStatus.ACTIVE,
                created_by=user.id,
            )
        )
    session.flush()

    result = alert_router.route(
        session,
        case1,
        candidate_photo_id=photo.id,
        similarity_score=0.75,
        tier="medium",
        actor_id=user.id,
    )
    session.flush()

    assert result["cluster_alert"] is True

    from app.models import AuditLog

    actions = [row.action for row in session.query(AuditLog).all()]
    assert "geo_alert" in actions
