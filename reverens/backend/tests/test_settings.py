# tests/test_settings.py
from tests.conftest import HEADERS


def test_get_settings_creates_default(client):
    resp = client.get("/api/settings", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold"] == 5
    assert data["email"] is None


def test_put_settings(client):
    client.put(
        "/api/settings",
        json={"email": "test@example.com", "tg_chat_id": "123456", "threshold": 10},
        headers=HEADERS,
    )
    resp = client.get("/api/settings", headers=HEADERS)
    assert resp.json()["email"] == "test@example.com"
    assert resp.json()["threshold"] == 10


def test_get_settings_idempotent(client):
    """Repeated GET does not create a second row."""
    client.get("/api/settings", headers=HEADERS)
    client.get("/api/settings", headers=HEADERS)
    resp = client.get("/api/settings", headers=HEADERS)
    assert resp.status_code == 200
