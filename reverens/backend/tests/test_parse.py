"""Tests for /api/parse/* endpoints."""
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
def set_keyword():
    with patch("api.routes.parse.settings") as mock_settings:
        mock_settings.apify_keyword = "телевизор Haier 55"
        yield mock_settings


WB_ITEMS = [
    {
        "product_id": "585984247",
        "name": "Телевизор 55 LED H1",
        "current_price": 29398,
        "supplier": "Haier Телевизоры",
        "product_url": "https://www.wildberries.ru/catalog/585984247/detail.aspx",
    },
]


class TestParseRun:
    def test_starts_run_and_returns_run_id(self, client, db, set_keyword):
        with patch("api.routes.parse.search_wb", new_callable=AsyncMock, return_value=WB_ITEMS):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"]
        assert data["status"] == "RUNNING"

    def test_returns_error_when_no_keyword(self, client, db, set_keyword):
        set_keyword.apify_keyword = ""
        resp = client.post("/api/parse/run", headers=HEADERS)
        assert resp.status_code == 400
        assert "APIFY_KEYWORD" in resp.json()["detail"]

    def test_returns_error_on_wb_failure(self, client, db, set_keyword):
        with patch("api.routes.parse.search_wb", new_callable=AsyncMock, side_effect=RuntimeError("WB API rate limit (429)")):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 502
        assert "429" in resp.json()["detail"]

    def test_saves_products_on_run(self, client, db, set_keyword):
        with patch("api.routes.parse.search_wb", new_callable=AsyncMock, return_value=WB_ITEMS):
            resp = client.post("/api/parse/run", headers=HEADERS)

        assert resp.status_code == 200
        product = db.query(Product).filter(Product.wb_article == "585984247").first()
        assert product is not None
        assert product.name == "Телевизор 55 LED H1"


class TestParseStatus:
    def test_returns_succeeded_with_count(self, client, db, set_keyword):
        with patch("api.routes.parse.search_wb", new_callable=AsyncMock, return_value=WB_ITEMS):
            run_resp = client.post("/api/parse/run", headers=HEADERS)
        run_id = run_resp.json()["run_id"]

        resp = client.get(f"/api/parse/status/{run_id}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCEEDED"
        assert data["updated"] == 1

    def test_returns_404_for_unknown_run(self, client):
        resp = client.get("/api/parse/status/nonexistent", headers=HEADERS)
        assert resp.status_code == 404

    def test_auto_creates_seller_and_price(self, client, db, set_keyword):
        with patch("api.routes.parse.search_wb", new_callable=AsyncMock, return_value=WB_ITEMS):
            run_resp = client.post("/api/parse/run", headers=HEADERS)

        product = db.query(Product).filter(Product.wb_article == "585984247").first()
        seller = db.query(Seller).filter(Seller.product_id == product.id).first()
        assert seller.seller_name == "Haier Телевизоры"

        prices = db.query(PriceHistory).filter(PriceHistory.seller_id == seller.id).all()
        assert len(prices) == 1
        assert prices[0].price == 29398


class TestParsePrice:
    def test_parses_price_with_currency(self):
        from api.routes.parse import _parse_price
        assert _parse_price("29 398 ₽") == 29398

    def test_parses_integer_price(self):
        from api.routes.parse import _parse_price
        assert _parse_price(29398) == 29398

    def test_returns_none_for_empty(self):
        from api.routes.parse import _parse_price
        assert _parse_price("") is None
        assert _parse_price("₽") is None
