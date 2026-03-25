# tests/test_auth.py
from tests.conftest import HEADERS


def test_no_api_key_returns_401(client):
    resp = client.get("/api/products", headers={})
    assert resp.status_code == 401


def test_wrong_api_key_returns_401(client):
    resp = client.get("/api/products", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_valid_api_key_passes_middleware(client):
    # Middleware lets the request through — 404 from empty router stub is better than 401 from middleware
    # After Task 4 this endpoint will return 200; for now we just check it's not 401
    resp = client.get("/api/products", headers=HEADERS)
    assert resp.status_code != 401
