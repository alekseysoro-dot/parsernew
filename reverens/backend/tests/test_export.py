# tests/test_export.py
from tests.conftest import HEADERS
from api.models import Product, Seller, PriceHistory


def test_export_csv_empty(client):
    resp = client.get("/api/export/csv", headers=HEADERS)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


def test_export_csv_with_data(client, db):
    product = Product(name="Ноут", wb_url="https://wildberries.ru/catalog/1/detail.aspx")
    db.add(product)
    db.flush()
    seller = Seller(product_id=product.id, seller_name="Продавец", seller_id="s1")
    db.add(seller)
    db.flush()
    db.add(PriceHistory(seller_id=seller.id, price=150000))
    db.commit()

    resp = client.get("/api/export/csv", headers=HEADERS)
    assert "Ноут" in resp.text
    assert "150000" in resp.text
