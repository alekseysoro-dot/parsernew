"""Tests for keywords CRUD endpoints."""

from tests.conftest import HEADERS


def test_list_keywords_empty(client):
    r = client.get("/api/keywords", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []


def test_create_keyword(client):
    r = client.post("/api/keywords", json={"keyword": "телевизор", "category": "Электроника"}, headers=HEADERS)
    assert r.status_code == 201
    data = r.json()
    assert data["keyword"] == "телевизор"
    assert data["category"] == "Электроника"
    assert data["is_active"] is True


def test_create_keyword_no_category(client):
    r = client.post("/api/keywords", json={"keyword": "куртка"}, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["category"] is None


def test_create_keyword_empty_rejected(client):
    r = client.post("/api/keywords", json={"keyword": "  "}, headers=HEADERS)
    assert r.status_code == 400


def test_list_keywords_returns_created(client):
    client.post("/api/keywords", json={"keyword": "телевизор"}, headers=HEADERS)
    client.post("/api/keywords", json={"keyword": "куртка"}, headers=HEADERS)
    r = client.get("/api/keywords", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_delete_keyword(client):
    r = client.post("/api/keywords", json={"keyword": "телевизор"}, headers=HEADERS)
    kw_id = r.json()["id"]
    r = client.delete(f"/api/keywords/{kw_id}", headers=HEADERS)
    assert r.status_code == 204
    r = client.get("/api/keywords", headers=HEADERS)
    assert len(r.json()) == 0


def test_delete_keyword_not_found(client):
    r = client.delete("/api/keywords/nonexistent", headers=HEADERS)
    assert r.status_code == 404


def test_toggle_keyword(client):
    r = client.post("/api/keywords", json={"keyword": "телевизор"}, headers=HEADERS)
    kw_id = r.json()["id"]
    assert r.json()["is_active"] is True

    r = client.patch(f"/api/keywords/{kw_id}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = client.patch(f"/api/keywords/{kw_id}", headers=HEADERS)
    assert r.json()["is_active"] is True


def test_toggle_keyword_not_found(client):
    r = client.patch("/api/keywords/nonexistent", headers=HEADERS)
    assert r.status_code == 404
