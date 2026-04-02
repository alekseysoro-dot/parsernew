"""Tests for wb_client.py — Wildberries search API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_response(status_code: int, json_data):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response
        mock_resp.raise_for_status.side_effect = HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )
    return mock_resp


WB_RESPONSE = {
    "products": [
        {
            "id": 585984247,
            "name": "Телевизор 55 LED H1",
            "brand": "Haier",
            "supplier": "Haier Телевизоры",
            "supplierId": 12345,
            "sizes": [
                {
                    "price": {
                        "basic": 4500000,
                        "product": 2939800,
                    }
                }
            ],
        },
        {
            "id": 678874481,
            "name": "Телевизор 55 LED H1",
            "brand": "Haier",
            "supplier": "ХОЛОДИЛЬНИК.ру GO",
            "supplierId": 67890,
            "sizes": [
                {
                    "price": {
                        "basic": 3500000,
                        "product": 2752900,
                    }
                }
            ],
        },
    ]
}


class TestSearchWb:
    @pytest.mark.asyncio
    async def test_returns_normalised_items(self):
        from api.wb_client import search_wb

        mock_resp = _make_response(200, WB_RESPONSE)

        with patch("api.wb_client.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_wb("телевизор Haier 55")

        assert len(result) == 2
        assert result[0]["product_id"] == "585984247"
        assert result[0]["name"] == "Телевизор 55 LED H1"
        assert result[0]["current_price"] == 29398
        assert result[0]["supplier"] == "Haier Телевизоры"
        assert "585984247" in result[0]["product_url"]

        assert result[1]["product_id"] == "678874481"
        assert result[1]["current_price"] == 27529

    @pytest.mark.asyncio
    async def test_raises_on_429(self):
        from api.wb_client import search_wb

        mock_resp = MagicMock()
        mock_resp.status_code = 429

        with patch("api.wb_client.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(RuntimeError, match="429"):
                await search_wb("test")

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_products(self):
        from api.wb_client import search_wb

        mock_resp = _make_response(200, {"products": []})

        with patch("api.wb_client.httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await search_wb("nonexistent")

        assert result == []


class TestExtractPrice:
    def test_extracts_sale_price(self):
        from api.wb_client import _extract_price
        product = {"sizes": [{"price": {"basic": 4500000, "product": 2939800}}]}
        assert _extract_price(product) == 29398

    def test_falls_back_to_basic(self):
        from api.wb_client import _extract_price
        product = {"sizes": [{"price": {"basic": 4500000}}]}
        assert _extract_price(product) == 45000

    def test_returns_none_for_no_sizes(self):
        from api.wb_client import _extract_price
        assert _extract_price({}) is None
        assert _extract_price({"sizes": []}) is None

    def test_returns_none_for_no_price(self):
        from api.wb_client import _extract_price
        assert _extract_price({"sizes": [{"price": {}}]}) is None
