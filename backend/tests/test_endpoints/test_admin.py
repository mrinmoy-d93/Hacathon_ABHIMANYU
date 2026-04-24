"""/api/admin — role-gated, threshold live update, CSV export (FRS §6.6)."""
from __future__ import annotations

import uuid

import pytest

from app.deps import invalidate_app_settings_cache
from app.models import AppSettings, Case, CaseStatus, User, UserRole
from app.services import audit_service, scoring_service


def _seed_case(db_session_factory, *, case_id: str = "KHJ-2020-00001", status: str = CaseStatus.ACTIVE) -> None:
    with db_session_factory() as session:
        session.add(
            Case(
                case_id=case_id,
                person_name="Lost Person",
                year_missing=2019,
                age_at_disappearance=7,
                last_seen_location="Ahmedabad",
                status=status,
            )
        )
        session.commit()


def test_non_admin_forbidden_from_dashboard(client, family_user, auth_headers):
    res = client.get("/api/admin/dashboard", headers=auth_headers(family_user))
    assert res.status_code == 403


def test_admin_dashboard_returns_counts(client, admin_user, auth_headers, db_session_factory):
    _seed_case(db_session_factory)
    res = client.get("/api/admin/dashboard", headers=auth_headers(admin_user))
    assert res.status_code == 200
    body = res.json()
    assert body["total_cases"] >= 1
    assert body["active_searches"] >= 1
    assert "confidence_distribution" in body
    assert "recent_activity" in body


def test_admin_cases_paginated(client, admin_user, auth_headers, db_session_factory):
    for i in range(3):
        _seed_case(db_session_factory, case_id=f"KHJ-2020-0000{i + 1}")
    res = client.get("/api/admin/cases?page=1&page_size=2", headers=auth_headers(admin_user))
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3


def test_admin_approve_and_reject_change_status(client, admin_user, auth_headers, db_session_factory):
    _seed_case(db_session_factory, case_id="KHJ-2020-00001")
    _seed_case(db_session_factory, case_id="KHJ-2020-00002")

    res = client.post("/api/admin/cases/KHJ-2020-00001/approve", headers=auth_headers(admin_user))
    assert res.status_code == 200
    assert res.json()["status"] == CaseStatus.UNDER_REVIEW

    res = client.post(
        "/api/admin/cases/KHJ-2020-00002/reject",
        json={"reason": "insufficient evidence"},
        headers=auth_headers(admin_user),
    )
    assert res.status_code == 200
    assert res.json()["status"] == CaseStatus.CLOSED


def test_settings_patch_takes_effect_on_next_scoring_call(
    client, admin_user, auth_headers, db_session_factory
):
    """FRS §6.6 Tab 4: no redeploy — threshold update changes the next call's tier."""
    headers = auth_headers(admin_user)

    # 1. Default thresholds — 0.85 lands in the "high" tier (>=0.80).
    with db_session_factory() as session:
        result = scoring_service.compute_confidence(session, similarity_score=0.70)
    assert result["tier"] == "high"  # (1+0.70)/2 = 0.85 → high

    # 2. Admin raises the auto-alert threshold past 0.85.
    res = client.patch(
        "/api/admin/settings",
        json={"auto_alert_threshold": 0.90},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["auto_alert_threshold"] == pytest.approx(0.90)

    # 3. Next scoring call sees the new threshold (0.85 now < 0.90 → medium).
    invalidate_app_settings_cache()
    with db_session_factory() as session:
        result2 = scoring_service.compute_confidence(session, similarity_score=0.70)
    assert result2["tier"] == "medium"


def test_settings_patch_validates_ranges(client, admin_user, auth_headers):
    # confidence_threshold above its max (0.90) must fail schema validation.
    res = client.patch(
        "/api/admin/settings",
        json={"confidence_threshold": 0.99},
        headers=auth_headers(admin_user),
    )
    assert res.status_code == 422


def test_settings_rejects_conflicting_values(client, admin_user, auth_headers):
    # confidence must be strictly less than auto_alert.
    res = client.patch(
        "/api/admin/settings",
        json={"confidence_threshold": 0.80, "auto_alert_threshold": 0.80},
        headers=auth_headers(admin_user),
    )
    assert res.status_code == 400


def test_audit_log_paginated_and_pii_redacted(client, admin_user, auth_headers, db_session_factory):
    # Write a few audit rows that include phone numbers so we can verify
    # redaction on export.
    with db_session_factory() as session:
        for i in range(3):
            audit_service.write_audit(
                session,
                action="auth.verify_otp",
                actor_id=admin_user.id,
                model_version=None,
                prompt_version=None,
                input_data={"phone": f"+9198765432{i:02d}"},
                output_data={"user_id": str(uuid.uuid4())},
            )
        session.commit()

    res = client.get("/api/admin/audit-log", headers=auth_headers(admin_user))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 3
    assert len(body["items"]) >= 3


def test_audit_log_export_csv_headers_and_redacts_pii(
    client, admin_user, auth_headers, db_session_factory
):
    with db_session_factory() as session:
        audit_service.write_audit(
            session,
            action="auth.verify_otp",
            actor_id=admin_user.id,
            model_version=None,
            prompt_version=None,
            input_data={"phone": "+919876543210"},
            output_data={"user_id": str(uuid.uuid4())},
        )
        session.commit()

    res = client.get("/api/admin/audit-log/export?format=csv", headers=auth_headers(admin_user))
    assert res.status_code == 200
    # Content-Disposition must trigger a download.
    disp = res.headers.get("content-disposition", "")
    assert "attachment" in disp and ".csv" in disp
    assert res.headers["content-type"].startswith("text/csv")
    # Body must not include the raw phone number (audit_service hashes + redacts).
    assert "+919876543210" not in res.text


def test_field_worker_assignment(client, admin_user, auth_headers, make_user):
    target = make_user("family", phone="+919900033333", name="Future Worker")
    res = client.post(
        "/api/admin/field-workers",
        json={"user_id": str(target.id), "zone": "Rajkot"},
        headers=auth_headers(admin_user),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["zone"] == "Rajkot"

    listing = client.get("/api/admin/field-workers", headers=auth_headers(admin_user))
    assert listing.status_code == 200
    names = [row["name"] for row in listing.json()]
    assert "Future Worker" in names
