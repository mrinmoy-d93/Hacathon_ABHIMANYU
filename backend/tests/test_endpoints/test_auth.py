"""/api/auth — register + demo OTP + admin 2FA (FRS §7.1, AC-11)."""
from __future__ import annotations

import os

import pytest

from app.config import get_settings
from app.deps import create_access_token
from app.models import User


@pytest.fixture(autouse=True)
def _demo_mode(monkeypatch):
    # Force DEMO_MODE=true for every auth test so the /send-otp endpoint short-
    # circuits and /verify-otp accepts the fixed OTP 123456.
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_OTP", "123456")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_register_creates_user_and_returns_id(client):
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Asha Patel",
            "phone": "+919876543210",
            "location": "Ahmedabad",
            "role": "family",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "user_id" in body and len(body["user_id"]) >= 16


def test_register_rejects_duplicate_phone(client):
    payload = {
        "name": "Asha Patel",
        "phone": "+919876543210",
        "location": "Ahmedabad",
        "role": "family",
    }
    client.post("/api/auth/register", json=payload)
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


def test_send_otp_demo_mode(client):
    res = client.post("/api/auth/send-otp", json={"phone": "+919876543210"})
    assert res.status_code == 200
    body = res.json()
    assert body["otp_sent"] is True
    assert body["demo_mode"] is True


def test_verify_otp_returns_jwt_for_family_user(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Asha",
            "phone": "+919876543210",
            "location": "Ahmedabad",
            "role": "family",
        },
    )
    res = client.post(
        "/api/auth/verify-otp",
        json={"phone": "+919876543210", "otp": "123456"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["access_token"]
    assert body["user"]["role"] == "family"
    assert body["token_type"] == "bearer"


def test_verify_otp_rejects_bad_otp(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Asha",
            "phone": "+919876543210",
            "location": "Ahmedabad",
            "role": "family",
        },
    )
    res = client.post(
        "/api/auth/verify-otp",
        json={"phone": "+919876543210", "otp": "000000"},
    )
    assert res.status_code == 401


def test_verify_otp_admin_requires_police_id(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Admin",
            "phone": "+919900000099",
            "location": "Ahmedabad",
            "role": "admin",
        },
    )
    # Without police_id → 401.
    without = client.post(
        "/api/auth/verify-otp",
        json={"phone": "+919900000099", "otp": "123456"},
    )
    assert without.status_code == 401

    # With the correct police_id → 200.
    good = client.post(
        "/api/auth/verify-otp",
        json={"phone": "+919900000099", "otp": "123456", "police_id": "KHOJO-ADMIN-2026"},
    )
    assert good.status_code == 200, good.text
    assert good.json()["user"]["role"] == "admin"


def test_protected_endpoint_accepts_valid_jwt(client, family_user, auth_headers):
    # Smoke-check: a JWT minted via create_access_token is accepted by
    # get_current_user. We probe via the /api/cases POST path which requires
    # family role.
    headers = auth_headers(family_user)
    payload = {
        "person_name": "Lost Child",
        "year_missing": 2019,
        "age_at_disappearance": 8,
        "last_seen_location": "Ahmedabad",
    }
    res = client.post("/api/cases", json=payload, headers=headers)
    assert res.status_code == 201


def test_protected_endpoint_rejects_missing_jwt(client):
    res = client.post(
        "/api/cases",
        json={
            "person_name": "x",
            "year_missing": 2020,
            "age_at_disappearance": 5,
            "last_seen_location": "y",
        },
    )
    assert res.status_code == 401


def test_protected_endpoint_rejects_invalid_jwt(client):
    res = client.post(
        "/api/cases",
        json={
            "person_name": "x",
            "year_missing": 2020,
            "age_at_disappearance": 5,
            "last_seen_location": "y",
        },
        headers={"Authorization": "Bearer not.a.valid.jwt"},
    )
    assert res.status_code == 401


def test_jwt_contains_role_claim(family_user):
    token, _ = create_access_token(str(family_user.id), family_user.role)
    from jose import jwt as jose_jwt

    settings = get_settings()
    payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["role"] == "family"
    assert payload["sub"] == str(family_user.id)
