"""Tests for /api/parse/* endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import HEADERS
from api.models import Product, Seller, PriceHistory


@pytest.fixture(autouse=True)
def clean_active_runs():
    yield
    from api.routes.parse import _active_runs
    _active_runs.clear()


@pytest.fixture(autouse=True)
def set_apify_keyword():
    with patch("api.routes.parse.settings") as mock_settings:
        mock_settings.apify_api_token = "test-token"
        mock_settings.apify_keyword = "телевизор Haier 55"
        yield mock_settings


class TestParseRun:
    def test_starts_run_and_returns_run_id(self, client, db, set_apify_keyword):
        mock_result = {"run_id": "run_abc", "dataset_id": "ds_xyz", "status": "RUNNING"}

        with patch("api.routes.parse.start_actor_run", new_callable=AsyncMock, return_value=mock_result):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"]
        assert data["status"] == "RUNNING"

    def test_returns_error_when_no_keyword(self, client, db, set_apify_keyword):
        set_apify_keyword.apify_keyword = ""
        resp = client.post("/api/parse/run", headers=HEADERS)
        assert resp.status_code == 400
        assert "APIFY_KEYWORD" in resp.json()["detail"]

    def test_returns_error_on_invalid_token(self, client, db, set_apify_keyword):
        with patch("api.routes.parse.start_actor_run", new_callable=AsyncMock, side_effect=RuntimeError("Invalid Apify token")):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 502
        assert "Invalid Apify token" in resp.json()["detail"]


class TestParseStatus:
    def test_returns_running_status(self, client, db):
        from api.routes.parse import _active_runs
        _active_runs["test-run-1"] = {
            "apify_run_id": "apify_run_abc",
            "dataset_id": "ds_xyz",
            "started_at": datetime.now(timezone.utc),
        }

        mock_status = {"status": "RUNNING", "dataset_id": "ds_xyz"}
        with patch("api.routes.parse.check_run_status", new_callable=AsyncMock, return_value=mock_status):
            resp = client.get("/api/parse/status/test-run-1", headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json()["status"] == "RUNNING"

    def test_returns_succeeded_and_auto_creates_product(self, client, db):
        from api.routes.parse import _active_runs
        _active_runs["test-run-2"] = {
            "apify_run_id": "apify_run_abc",
            "dataset_id": "ds_xyz",
            "started_at": datetime.now(timezone.utc),
        }

        mock_status = {"status": "SUCCEEDED", "dataset_id": "ds_xyz"}
        mock_items = [
            {
                "product_id": "585984247",
                "name": "Телевизор 55 LED H1",
                "current_price": "29 398 ₽",
                "supplier": "Haier Телевизоры",
                "product_url": "https://www.wildberries.ru/catalog/585984247/detail.aspx",
            },
        ]

        with patch("api.routes.parse.check_run_status", new_callable=AsyncMock, return_value=mock_status), \
             patch("api.routes.parse.fetch_dataset_items", new_callable=AsyncMock, return_value=mock_items):
            resp = client.get("/api/parse/status/test-run-2", headers=HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCEEDED"
        assert data["updated"] == 1

        product = db.query(Product).filter(Product.wb_article == "585984247").first()
        assert product is not None
        assert product.name == "Телевизор 55 LED H1"

        seller = db.query(Seller).filter(Seller.product_id == product.id).first()
        assert seller.seller_name == "Haier Телевизоры"

        prices = db.query(PriceHistory).filter(PriceHistory.seller_id == seller.id).all()
        assert len(prices) == 1
        assert prices[0].price == 29398

    def test_returns_404_for_unknown_run(self, client):
        resp = client.get("/api/parse/status/nonexistent", headers=HEADERS)
        assert resp.status_code == 404

    def test_returns_failed_status(self, client, db):
        from api.routes.parse import _active_runs
        _active_runs["test-run-3"] = {
            "apify_run_id": "apify_run_fail",
            "dataset_id": None,
            "started_at": datetime.now(timezone.utc),
        }

        mock_status = {"status": "FAILED", "dataset_id": None}
        with patch("api.routes.parse.check_run_status", new_callable=AsyncMock, return_value=mock_status):
            resp = client.get("/api/parse/status/test-run-3", headers=HEADERS)

        assert resp.status_code == 200
        assert resp.json()["status"] == "FAILED"


class TestParsePrice:
    def test_parses_price_with_currency(self):
        from api.routes.parse import _parse_price
        assert _parse_price("29 398 ₽") == 29398

    def test_parses_price_without_spaces(self):
        from api.routes.parse import _parse_price
        assert _parse_price("15000₽") == 15000

    def test_returns_none_for_empty(self):
        from api.routes.parse import _parse_price
        assert _parse_price("") is None
        assert _parse_price("₽") is None
