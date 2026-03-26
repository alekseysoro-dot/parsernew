"""Tests for /api/parse/* endpoints."""
from unittest.mock import AsyncMock, patch

from tests.conftest import HEADERS
from api.models import Product


class TestParseRun:
    def test_starts_run_and_returns_run_id(self, client, db):
        product = Product(name="Test Product", wb_url="https://www.wildberries.ru/catalog/12345/detail.aspx", wb_article="12345")
        db.add(product)
        db.commit()

        mock_result = {"run_id": "run_abc", "dataset_id": "ds_xyz", "status": "RUNNING"}

        with patch("api.routes.parse.start_actor_run", new_callable=AsyncMock, return_value=mock_result):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"]  # UUID, not empty
        assert data["status"] == "RUNNING"
        assert data["total_products"] == 1

    def test_returns_error_when_no_products(self, client, db):
        resp = client.post("/api/parse/run", headers=HEADERS)
        assert resp.status_code == 400
        assert "No products" in resp.json()["detail"]

    def test_returns_error_on_invalid_token(self, client, db):
        product = Product(name="Test", wb_url="https://www.wildberries.ru/catalog/12345/detail.aspx", wb_article="12345")
        db.add(product)
        db.commit()

        with patch("api.routes.parse.start_actor_run", new_callable=AsyncMock, side_effect=RuntimeError("Invalid Apify token")):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 502
        assert "Invalid Apify token" in resp.json()["detail"]
