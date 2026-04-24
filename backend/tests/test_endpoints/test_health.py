"""GET /health — liveness + provider signals (FRS NFR-2, NFR-8)."""
from __future__ import annotations


def test_health_returns_expected_shape(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    providers = body["providers"]
    assert set(providers.keys()) == {"openai", "groq", "hf", "replicate"}
    assert "uptime_seconds" in body
    assert "version" in body


def test_health_attaches_request_id(client):
    res = client.get("/health")
    assert "x-request-id" in res.headers
    assert len(res.headers["x-request-id"]) >= 8
