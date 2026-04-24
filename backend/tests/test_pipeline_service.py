from __future__ import annotations

import uuid

from app.models import AuditLog, Case, CaseStatus, Photo, User, UserRole
from app.services import alert_router, pipeline_service


def _seed_case_with_photos(session, monkeypatch):
    alert_router._geocode.cache_clear()
    monkeypatch.setattr(alert_router, "_geocode", lambda loc: (23.03, 72.58) if loc else None)

    family = User(name="parent", phone="+919811200001", location="Ahmedabad", role=UserRole.FAMILY)
    worker = User(name="worker", phone="+919811200002", location="Ahmedabad", role=UserRole.FIELD_WORKER)
    session.add_all([family, worker])
    session.flush()

    case = Case(
        case_id="KHJ-2024-00042",
        person_name="Arjun Desai",
        year_missing=2009,
        age_at_disappearance=10,
        last_seen_location="Ahmedabad",
        status=CaseStatus.ACTIVE,
        created_by=family.id,
    )
    session.add(case)
    session.flush()

    for age in (10, 12):
        session.add(
            Photo(
                id=uuid.uuid4(),
                case_id=case.case_id,
                supabase_url=f"https://demo.supabase/case-photos/{case.case_id}/age_{age}.jpg",
                age_at_photo=age,
                embedding=None,  # forces detect+embed during pipeline
            )
        )

    # Seed a "sighting" candidate on a different case so find_matches has data.
    other_case = Case(
        case_id="KHJ-2024-00099",
        person_name="Unknown",
        year_missing=2020,
        age_at_disappearance=20,
        last_seen_location="Surat",
        status=CaseStatus.UNDER_REVIEW,
        created_by=family.id,
    )
    session.add(other_case)
    session.flush()
    session.add(
        Photo(
            id=uuid.uuid4(),
            case_id=other_case.case_id,
            supabase_url="https://demo.supabase/case-photos/sighting-1.jpg",
            age_at_photo=27,
            embedding=[0.1] * 512,
        )
    )
    session.commit()
    return case, worker


def test_process_case_end_to_end_in_mock_mode(session, monkeypatch):
    case, worker = _seed_case_with_photos(session, monkeypatch)

    result = pipeline_service.process_case(session, case.case_id, actor_id=worker.id)

    assert result["case_id"] == case.case_id
    assert result["aged_photo_url"].startswith("https://placehold.co/")
    assert result["providers_used"]["aging"] == "mock"
    assert result["providers_used"]["llm"] == "template"
    assert result["summary"]
    assert "KHJ-2024-00042" in result["summary"]
    assert result["processing_time_seconds"] >= 0
    # One aged photo + the two source photos = 3 photo rows for the case.
    case_photos = session.query(Photo).filter(Photo.case_id == case.case_id).all()
    assert any(p.is_predicted_aged for p in case_photos)

    # Pipeline invocation audit must exist.
    pipeline_events = session.query(AuditLog).filter(AuditLog.action == "pipeline.process_case").all()
    assert len(pipeline_events) == 1


def test_process_case_raises_for_insufficient_photos(session, monkeypatch):
    from app.services.ai_common import InsufficientPhotosError

    family = User(name="p", phone="+919811300001", location="X", role=UserRole.FAMILY)
    session.add(family)
    session.flush()
    case = Case(
        case_id="KHJ-2024-00500",
        person_name="Test",
        year_missing=2015,
        age_at_disappearance=5,
        last_seen_location="X",
        created_by=family.id,
    )
    session.add(case)
    session.add(
        Photo(
            id=uuid.uuid4(),
            case_id=case.case_id,
            supabase_url="x",
            age_at_photo=5,
        )
    )
    session.commit()

    try:
        pipeline_service.process_case(session, case.case_id)
    except InsufficientPhotosError:
        pass
    else:
        raise AssertionError("expected InsufficientPhotosError")
