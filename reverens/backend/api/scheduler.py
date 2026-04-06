"""
APScheduler tasks:
- scheduled_parse: every 3 hours — search WB for all active keywords, write prices to DB
- cleanup_old_prices: daily at 03:00 — delete records older than 180 days
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

from api.config import settings
from api.db import SessionLocal
from api.models import Keyword, PriceHistory, Product, Seller
from api.notifier import check_price_alerts
from api.wb_client import search_wb

logger = logging.getLogger(__name__)

PAUSE_BETWEEN_KEYWORDS = 60


def _parse_price(raw) -> int | None:
    """Extract integer price from string '29 398 ₽' or pass through int."""
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


async def scheduled_parse() -> None:
    """Search WB for all active keywords and write prices to DB."""
    db = SessionLocal()
    try:
        kw_list = db.query(Keyword).filter(Keyword.is_active.is_(True)).all()
        keyword_strings = [kw.keyword for kw in kw_list]

        if not keyword_strings and settings.apify_keyword:
            keyword_strings = [settings.apify_keyword]

        if not keyword_strings:
            logger.warning("No keywords configured, skipping scheduled parse")
            return

        total_written = 0
        # Build keyword -> category map
        kw_categories = {kw.keyword: kw.category for kw in kw_list}

        for i, keyword in enumerate(keyword_strings):
            if i > 0:
                logger.info(f"Pausing {PAUSE_BETWEEN_KEYWORDS}s before next keyword...")
                await asyncio.sleep(PAUSE_BETWEEN_KEYWORDS)

            try:
                logger.info(f"Parsing keyword {i+1}/{len(keyword_strings)}: {keyword}")
                items = await search_wb(keyword)
                written = _save_prices(items, db, group_name=kw_categories.get(keyword))
                total_written += written
                logger.info(f"Keyword '{keyword}': {written} prices written")
            except Exception:
                logger.exception(f"Error parsing keyword '{keyword}', continuing...")

        logger.info(f"Scheduled parse complete: {total_written} prices for {len(keyword_strings)} keywords")

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


def _save_prices(items: list[dict], db, group_name: str | None = None) -> int:
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
                group_name=group_name,
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
