"""Tests for the scheduler (WB-based)."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from api.models import Keyword, PriceHistory, Product, Seller


WB_ITEMS = [
    {
        "product_id": "585984247",
        "name": "Телевизор 55 LED H1",
        "current_price": 29398,
        "supplier": "Haier Телевизоры",
        "product_url": "https://www.wildberries.ru/catalog/585984247/detail.aspx",
    },
    {
        "product_id": "678874481",
        "name": "Телевизор 55 LED H1",
        "current_price": 27529,
        "supplier": "ХОЛОДИЛЬНИК.ру GO",
        "product_url": "https://www.wildberries.ru/catalog/678874481/detail.aspx",
    },
]


class TestScheduledParse:
    def test_uses_keywords_from_db(self, db):
        """Scheduler picks active keywords from DB."""
        db.add(Keyword(keyword="телевизор Haier 55", is_active=True))
        db.add(Keyword(keyword="inactive keyword", is_active=False))
        db.commit()

        mock_search = AsyncMock(return_value=WB_ITEMS)

        original_close = db.close
        db.close = lambda: None

        with patch("api.scheduler.search_wb", mock_search), \
             patch("api.scheduler.SessionLocal", return_value=db), \
             patch("api.scheduler.asyncio.sleep", new_callable=AsyncMock):

            from api.scheduler import scheduled_parse
            asyncio.run(scheduled_parse())

        db.close = original_close

        mock_search.assert_called_once_with("телевизор Haier 55")

        products = db.query(Product).all()
        assert len(products) == 2

        prices = db.query(PriceHistory).all()
        assert len(prices) == 2
        assert {p.price for p in prices} == {29398, 27529}

    def test_skips_when_no_keywords(self, db):
        """When no active keywords in DB, scheduler does nothing (no env fallback)."""
        mock_search = AsyncMock(return_value=WB_ITEMS)

        original_close = db.close
        db.close = lambda: None

        with patch("api.scheduler.search_wb", mock_search), \
             patch("api.scheduler.SessionLocal", return_value=db):

            from api.scheduler import scheduled_parse
            asyncio.run(scheduled_parse())

        db.close = original_close

        mock_search.assert_not_called()
        assert db.query(Product).count() == 0


class TestCleanupOldPrices:
    def test_deletes_old_records(self, db):
        product = Product(name="Test", wb_url="https://wb.ru/catalog/1/detail.aspx", wb_article="1")
        db.add(product)
        db.commit()

        seller = Seller(product_id=product.id, seller_name="S", seller_id="s1")
        db.add(seller)
        db.commit()

        old = PriceHistory(seller_id=seller.id, price=100, recorded_at=datetime.now(timezone.utc) - timedelta(days=200))
        fresh = PriceHistory(seller_id=seller.id, price=200, recorded_at=datetime.now(timezone.utc))
        db.add_all([old, fresh])
        db.commit()

        seller_id = seller.id

        original_close = db.close
        db.close = lambda: None

        with patch("api.scheduler.SessionLocal", return_value=db):
            from api.scheduler import cleanup_old_prices
            cleanup_old_prices()

        db.close = original_close

        remaining = db.query(PriceHistory).filter(PriceHistory.seller_id == seller_id).all()
        assert len(remaining) == 1
        assert remaining[0].price == 200
