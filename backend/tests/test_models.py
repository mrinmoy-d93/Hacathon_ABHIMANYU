from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import pytest

from app.models import (
    AuditLog,
    AuditLogImmutableError,
    Case,
    CaseStatus,
    Match,
    MatchStatus,
    MatchTier,
    NotMatchFeedback,
    Photo,
    User,
    UserRole,
)
from app.utils.case_id import generate_case_id

CASE_ID_RE = re.compile(r"^KHJ-\d{4}-\d{5}$")


def _make_user(session, *, role=UserRole.FAMILY, phone="+919811100001") -> User:
    user = User(name="Test", phone=phone, location="Ahmedabad", role=role)
    session.add(user)
    session.flush()
    return user


def _make_case(session, creator: User, case_id: str = "KHJ-2024-00001") -> Case:
    case = Case(
        case_id=case_id,
        person_name="Arjun",
        year_missing=2009,
        age_at_disappearance=10,
        last_seen_location="Ahmedabad",
        created_by=creator.id,
    )
    session.add(case)
    session.flush()
    return case


def test_user_case_photo_relationships(session):
    creator = _make_user(session)
    case = _make_case(session, creator)
    photo = Photo(
        case_id=case.case_id,
        supabase_url="https://test.supabase.co/storage/v1/object/public/case-photos/x.jpg",
        age_at_photo=10,
        embedding=[0.0] * 512,
    )
    session.add(photo)
    session.commit()

    session.refresh(case)
    assert len(case.photos) == 1
    assert case.photos[0].id == photo.id
    assert case.creator.id == creator.id
    assert creator.cases[0].case_id == case.case_id


def test_case_id_format_matches_spec(session):
    generated = generate_case_id(session, 2024)
    assert CASE_ID_RE.fullmatch(generated), generated
    assert generated == "KHJ-2024-00001"


def test_case_id_increments_between_calls(session):
    creator = _make_user(session)
    first = generate_case_id(session, 2024)
    session.add(
        Case(
            case_id=first,
            person_name="A",
            year_missing=2010,
            age_at_disappearance=5,
            last_seen_location="X",
            created_by=creator.id,
        )
    )
    session.flush()
    second = generate_case_id(session, 2024)
    assert second == "KHJ-2024-00002"


def test_predicted_current_age_2026(monkeypatch):
    import app.models.case as case_module

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 4, 24, tzinfo=tz)

    monkeypatch.setattr(case_module, "datetime", _Frozen)

    case = Case(
        case_id="KHJ-2009-00001",
        person_name="Arjun",
        year_missing=2009,
        age_at_disappearance=10,
        last_seen_location="Ahmedabad",
    )
    assert case.predicted_current_age == 27


def test_match_relationships(session):
    creator = _make_user(session)
    worker = _make_user(session, role=UserRole.FIELD_WORKER, phone="+919811100002")
    case = _make_case(session, creator)
    photo = Photo(
        case_id=case.case_id,
        supabase_url="https://test.supabase.co/storage/v1/object/public/case-photos/a.jpg",
        age_at_photo=12,
    )
    session.add(photo)
    session.flush()

    match = Match(
        case_id=case.case_id,
        candidate_photo_id=photo.id,
        confidence_score=0.85,
        tier=MatchTier.HIGH,
        status=MatchStatus.PENDING,
        field_worker_id=worker.id,
    )
    session.add(match)
    session.flush()

    feedback = NotMatchFeedback(
        match_id=match.id,
        real_photo_url="https://test.supabase.co/storage/v1/object/public/not-match-photos/y.jpg",
        error_vector={"nose": 0.12, "jaw": 0.08},
    )
    session.add(feedback)
    session.commit()

    session.refresh(match)
    assert match.case.case_id == case.case_id
    assert match.candidate_photo.id == photo.id
    assert match.field_worker.id == worker.id
    assert match.not_match_feedback is not None
    assert match.not_match_feedback.error_vector["nose"] == 0.12


def test_audit_log_rejects_update(session):
    row = AuditLog(
        timestamp=datetime.now(timezone.utc),
        actor_id=uuid.uuid4(),
        action="test",
        input_hash="a" * 64,
        output_hash="b" * 64,
        hmac_signature="c" * 64,
    )
    session.add(row)
    session.commit()

    row.action = "tampered"
    with pytest.raises(AuditLogImmutableError):
        session.commit()
    session.rollback()


def test_audit_log_rejects_delete(session):
    row = AuditLog(
        timestamp=datetime.now(timezone.utc),
        action="test",
        input_hash="a" * 64,
        output_hash="b" * 64,
        hmac_signature="c" * 64,
    )
    session.add(row)
    session.commit()

    session.delete(row)
    with pytest.raises(AuditLogImmutableError):
        session.commit()
    session.rollback()
