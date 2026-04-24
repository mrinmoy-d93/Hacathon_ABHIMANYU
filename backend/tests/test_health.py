from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime_seconds" in body
    assert "providers" in body
    assert set(body["providers"].keys()) == {"openai", "groq", "hf", "replicate"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()


def test_health_has_request_id_header():
    response = client.get("/health")
    assert "x-request-id" in response.headers
