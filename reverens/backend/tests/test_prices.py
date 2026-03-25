# tests/test_prices.py
import pytest
from datetime import datetime, timedelta
from tests.conftest import HEADERS, make_uuid
from api.models import Product, Seller, PriceHistory


def _seed_product_with_prices(db, n_prices=2):
    """Create product -> seller -> N price records."""
    product = Product(name="Тест", wb_url="https://wildberries.ru/catalog/1/detail.aspx")
    db.add(product)
    db.flush()

    seller = Seller(product_id=product.id, seller_name="ООО Продавец", seller_id="s1")
    db.add(seller)
    db.flush()

    now = datetime.utcnow()
    for i in range(n_prices):
        ph = PriceHistory(
            seller_id=seller.id,
            price=1000 + i * 100,
            recorded_at=now - timedelta(hours=n_prices - i),
        )
        db.add(ph)
    db.commit()
    return product.id


def test_prices_latest(client, db):
    product_id = _seed_product_with_prices(db, n_prices=2)
    resp = client.get(f"/api/prices/{product_id}", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["latest_price"] == 1100   # last price
    assert data[0]["prev_price"] == 1000
    assert data[0]["delta_pct"] == pytest.approx(10.0)


def test_prices_history(client, db):
    product_id = _seed_product_with_prices(db, n_prices=3)
    resp = client.get(f"/api/prices/{product_id}/history?days=30", headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_prices_delta(client, db):
    product_id = _seed_product_with_prices(db, n_prices=2)
    resp = client.get(f"/api/prices/{product_id}/delta", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_delta"] == pytest.approx(10.0)
