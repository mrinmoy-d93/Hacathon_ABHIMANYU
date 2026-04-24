"""/api/cases — create, upload photo, reject with <2 photos, result polling."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from app.models import Case, Photo
from app.services import supabase_service


@pytest.fixture(autouse=True)
def _mock_supabase_upload(monkeypatch):
    def _fake_upload(file_bytes, bucket, case_id, filename=None, content_type=None):
        return f"https://fake-supabase.test/{bucket}/{case_id}/{filename or 'photo.jpg'}"

    monkeypatch.setattr(supabase_service, "upload_photo", _fake_upload)
    yield


def _create_case(client, headers, *, year_missing=2019):
    payload = {
        "person_name": "Lost Child",
        "year_missing": year_missing,
        "age_at_disappearance": 7,
        "last_seen_location": "Ahmedabad",
        "identifying_marks": "small scar on left cheek",
    }
    return client.post("/api/cases", json=payload, headers=headers)


def test_create_case_returns_khj_id_and_predicted_age(client, family_user, auth_headers):
    headers = auth_headers(family_user)
    res = _create_case(client, headers, year_missing=2020)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["case_id"].startswith("KHJ-2020-")
    expected_age = 7 + (datetime.now(timezone.utc).year - 2020)
    assert body["predicted_current_age"] == expected_age


def test_create_case_rejects_future_year(client, family_user, auth_headers):
    headers = auth_headers(family_user)
    future = datetime.now(timezone.utc).year + 1
    payload = {
        "person_name": "Lost Child",
        "year_missing": future,
        "age_at_disappearance": 5,
        "last_seen_location": "Ahmedabad",
    }
    res = client.post("/api/cases", json=payload, headers=headers)
    assert res.status_code == 400


def test_create_case_requires_family_role(client, field_worker_user, auth_headers):
    headers = auth_headers(field_worker_user)
    res = _create_case(client, headers)
    assert res.status_code == 403


def test_upload_photo_returns_public_url(client, family_user, auth_headers):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]
    files = {"file": ("baby.jpg", io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"0" * 100), "image/jpeg")}
    res = client.post(
        f"/api/cases/{case_id}/photos",
        data={"age_at_photo": "3"},
        files=files,
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "photo_id" in body
    assert body["supabase_url"].startswith("https://fake-supabase.test/")


def test_upload_photo_rejects_empty_file(client, family_user, auth_headers):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    res = client.post(
        f"/api/cases/{case_id}/photos",
        data={"age_at_photo": "3"},
        files=files,
        headers=headers,
    )
    assert res.status_code == 400


def test_process_rejects_with_fewer_than_two_photos(client, family_user, auth_headers):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]
    # Only upload one photo.
    files = {"file": ("a.jpg", io.BytesIO(b"fake"), "image/jpeg")}
    client.post(
        f"/api/cases/{case_id}/photos",
        data={"age_at_photo": "3"},
        files=files,
        headers=headers,
    )
    res = client.post(f"/api/cases/{case_id}/process", headers=headers)
    assert res.status_code == 400
    assert "FR-2.3" in res.json()["error"]


def test_process_accepts_with_two_photos_and_returns_job(client, family_user, auth_headers, db_session_factory):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]
    for age in (3, 10):
        files = {"file": (f"{age}.jpg", io.BytesIO(b"fake"), "image/jpeg")}
        client.post(
            f"/api/cases/{case_id}/photos",
            data={"age_at_photo": str(age)},
            files=files,
            headers=headers,
        )
    res = client.post(f"/api/cases/{case_id}/process", headers=headers)
    assert res.status_code == 202
    body = res.json()
    assert body["status"] == "processing"
    assert body["job_id"]


def test_result_polling_shape(client, family_user, auth_headers):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]
    res = client.get(f"/api/cases/{case_id}/result", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"unknown", "processing", "complete"}
    assert "confidence_distribution" in body
    assert "explanation" in body
    # FRS FR-4.4 disclaimer must appear.
    assert "Artificial Intelligence" in body["explanation"]


def test_get_case_denies_other_family_users(client, make_user, auth_headers, family_user):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]

    intruder = make_user("family", phone="+919900099099", name="Intruder")
    res = client.get(f"/api/cases/{case_id}", headers=auth_headers(intruder))
    assert res.status_code == 403


def test_get_case_allows_admin(client, family_user, admin_user, auth_headers):
    headers = auth_headers(family_user)
    case_id = _create_case(client, headers).json()["case_id"]
    res = client.get(f"/api/cases/{case_id}", headers=auth_headers(admin_user))
    assert res.status_code == 200
    assert res.json()["case_id"] == case_id
