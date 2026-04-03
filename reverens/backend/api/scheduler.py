"""
APScheduler tasks:
- scheduled_parse: every 3 hours — search WB, write prices to DB
- cleanup_old_prices: daily at 03:00 — delete records older than 180 days
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from api.config import settings
from api.db import SessionLocal
from api.models import PriceHistory, Product, Seller
from api.notifier import check_price_alerts
from api.wb_client import search_wb

logger = logging.getLogger(__name__)


def _parse_price(raw) -> int | None:
    """Extract integer price from string '29 398 ₽' or pass through int."""
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


async def scheduled_parse() -> None:
    """Search WB by keyword and write prices to DB."""
    keyword = settings.apify_keyword
    if not keyword:
        logger.warning("APIFY_KEYWORD not configured, skipping scheduled parse")
        return

    db = SessionLocal()
    try:
        logger.info(f"Starting scheduled parse with keyword: {keyword}")
        items = await search_wb(keyword)
        written = _save_prices(items, db)
        logger.info(f"Scheduled parse complete: {written} prices written")

        try:
            alerts = check_price_alerts(db)
            if alerts:
                logger.info(f"Sent {alerts} price alert(s)")
        except Exception:
            logger.exception("Error checking price alerts")

    except Exception:
        db.rollback()
        logger.exception("Error during scheduled parse")
    finally:
        db.close()


def _save_prices(items: list[dict], db) -> int:
    """Save WB search results: auto-create Products, Sellers, write prices."""
    written = 0
    for item in items:
        article = str(item.get("product_id", ""))
        if not article:
            continue

        price = _parse_price(item.get("current_price", ""))
        if not price:
            logger.warning(f"No price for article {article}")
            continue

        product = db.query(Product).filter(Product.wb_article == article).first()
        if not product:
            product = Product(
                name=item.get("name", ""),
                wb_article=article,
                wb_url=item.get("product_url", ""),
            )
            db.add(product)
            db.flush()

        supplier_name = item.get("supplier", "Unknown")

        seller = (
            db.query(Seller)
            .filter(Seller.product_id == product.id, Seller.seller_name == supplier_name)
            .first()
        )
        if not seller:
            seller = Seller(product_id=product.id, seller_name=supplier_name, seller_id=supplier_name)
            db.add(seller)
            db.flush()

        db.add(PriceHistory(seller_id=seller.id, price=price))
        written += 1

    db.commit()
    return written


def cleanup_old_prices() -> None:
    """Delete price_history records older than 180 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    db = SessionLocal()
    try:
        deleted = db.query(PriceHistory).filter(PriceHistory.recorded_at < cutoff).delete()
        db.commit()
        logger.info(f"Cleanup: deleted {deleted} old records")
    finally:
        db.close()
