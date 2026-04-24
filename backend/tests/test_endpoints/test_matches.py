"""/api/matches — confirm flow + mandatory real_photo on not-match (FRS §6.5)."""
from __future__ import annotations

import io
import uuid

import pytest

from app.models import (
    Case,
    CaseStatus,
    Match,
    MatchStatus,
    MatchTier,
    NotMatchFeedback,
    Photo,
)
from app.services import llm_service, supabase_service


@pytest.fixture(autouse=True)
def _mock_supabase_upload(monkeypatch):
    def _fake_upload(file_bytes, bucket, case_id, filename=None, content_type=None):
        return f"https://fake-supabase.test/{bucket}/{case_id}/{filename or 'photo.jpg'}"

    monkeypatch.setattr(supabase_service, "upload_photo", _fake_upload)
    yield


def _seed_case_and_match(db_session_factory, field_worker_id: uuid.UUID, *, tier: str = "medium") -> str:
    with db_session_factory() as session:
        case = Case(
            case_id="KHJ-2020-00001",
            person_name="Lost Person",
            year_missing=2019,
            age_at_disappearance=7,
            last_seen_location="Ahmedabad",
            status=CaseStatus.ACTIVE,
        )
        photo = Photo(
            id=uuid.uuid4(),
            case_id=case.case_id,
            supabase_url="https://fake-supabase.test/case-photos/x.jpg",
            age_at_photo=14,
            embedding=[0.1] * 512,
        )
        match = Match(
            id=uuid.uuid4(),
            case_id=case.case_id,
            candidate_photo_id=photo.id,
            confidence_score=0.72,
            tier=tier,
            status=MatchStatus.PENDING,
            field_worker_id=field_worker_id,
        )
        session.add_all([case, photo, match])
        session.commit()
        return str(match.id)


def test_pending_returns_matches_for_worker(client, field_worker_user, auth_headers, db_session_factory):
    _seed_case_and_match(db_session_factory, field_worker_user.id)
    res = client.get("/api/matches/pending", headers=auth_headers(field_worker_user))
    assert res.status_code == 200
    rows = res.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["person_name"] == "Lost Person"
    assert "Artificial Intelligence" in row["explanation"]


def test_pending_forbidden_for_family(client, family_user, auth_headers):
    res = client.get("/api/matches/pending", headers=auth_headers(family_user))
    assert res.status_code == 403


def test_confirm_triggers_family_alert_and_updates_case(
    client, field_worker_user, auth_headers, db_session_factory, monkeypatch
):
    calls: list[tuple] = []

    def _fake_alert(case, match, session=None, actor_id=None):
        calls.append((case, match))
        return {
            "text": "family alert text",
            "provider": "template",
            "model_version": "template/standard",
            "prompt_version": "v1",
            "tokens_used": None,
        }

    monkeypatch.setattr(llm_service, "generate_family_alert", _fake_alert)
    match_id = _seed_case_and_match(db_session_factory, field_worker_user.id)
    res = client.post(f"/api/matches/{match_id}/confirm", headers=auth_headers(field_worker_user))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["confirmed"] is True
    assert body["family_notified"] is True
    assert body["provider_used"] == "template"
    assert calls, "generate_family_alert should be invoked"

    with db_session_factory() as session:
        match = session.get(Match, uuid.UUID(match_id))
        assert match.status == MatchStatus.CONFIRMED
        assert match.case.status == CaseStatus.FOUND


def test_confirm_rejects_if_not_assigned(
    client, make_user, auth_headers, field_worker_user, db_session_factory
):
    match_id = _seed_case_and_match(db_session_factory, field_worker_user.id)
    intruder = make_user("field_worker", phone="+919900077777", name="Intruder")
    res = client.post(f"/api/matches/{match_id}/confirm", headers=auth_headers(intruder))
    assert res.status_code == 403


def test_not_match_rejects_without_real_photo(client, field_worker_user, auth_headers, db_session_factory):
    match_id = _seed_case_and_match(db_session_factory, field_worker_user.id)
    # Simulate an empty upload: real_photo is required but empty.
    files = {"real_photo": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    res = client.post(
        f"/api/matches/{match_id}/not-match",
        files=files,
        headers=auth_headers(field_worker_user),
    )
    assert res.status_code == 400
    assert "mandatory" in res.json()["error"].lower() or "FR-5.4" in res.json()["error"]


def test_not_match_happy_path_captures_error_vector(
    client, field_worker_user, auth_headers, db_session_factory
):
    match_id = _seed_case_and_match(db_session_factory, field_worker_user.id)
    files = {"real_photo": ("actual.jpg", io.BytesIO(b"real-jpg-bytes"), "image/jpeg")}
    res = client.post(
        f"/api/matches/{match_id}/not-match",
        files=files,
        headers=auth_headers(field_worker_user),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["error_vector_captured"] is True
    assert body["case_reopened"] is True
    assert body["feedback_pool_size"] == 1
    assert body["training_cycle_triggered"] is False

    with db_session_factory() as session:
        row = session.query(NotMatchFeedback).one()
        assert set(row.error_vector.keys()) == {
            "nose",
            "cheekbone",
            "jawline",
            "eye_spacing",
            "forehead_width",
        }
        assert session.get(Match, uuid.UUID(match_id)).status == MatchStatus.NOT_MATCH
        assert session.get(Case, "KHJ-2020-00001").status == CaseStatus.ACTIVE
