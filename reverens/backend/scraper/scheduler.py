"""
Task scheduler:
- update_all_prices: every 3 hours
- cleanup_old_prices: every day at 03:00
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.config import settings
from scraper.notifier import notify_if_needed
from scraper.wb_api import fetch_product_info, fetch_seller_price
from scraper.wb_scraper import scrape_seller_price

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


def update_all_prices() -> None:
    """Update prices for all products from all sellers."""
    from api.models import NotificationSettings, PriceHistory, Product, Seller

    logger.info("Starting price update")
    db = Session()
    price_changes = []

    try:
        products = db.query(Product).all()
        for product in products:
            if not product.wb_article:
                continue

            info = fetch_product_info(product.wb_article)
            if not info:
                logger.warning(f"WB API returned empty for article {product.wb_article}")
                continue

            # Sync sellers
            existing_sellers = {s.seller_id: s for s in product.sellers}
            for seller_data in info["sellers"]:
                seller = existing_sellers.get(seller_data["seller_id"])
                if not seller:
                    seller = Seller(
                        product_id=product.id,
                        seller_id=seller_data["seller_id"],
                        seller_name=seller_data["seller_name"],
                    )
                    db.add(seller)
                    db.flush()

                # Get price
                price = fetch_seller_price(product.wb_article, seller.seller_id)
                if price is None:
                    logger.info(f"API didn't return price for {seller.seller_name}, trying Playwright")
                    price = scrape_seller_price(product.wb_article, seller.seller_id)

                if price is None:
                    logger.warning(f"Could not get price for {seller.seller_name}")
                    continue

                # Compare with previous price
                prev = (
                    db.query(PriceHistory)
                    .filter(PriceHistory.seller_id == seller.id)
                    .order_by(PriceHistory.recorded_at.desc())
                    .first()
                )

                if prev and prev.price != 0:
                    delta = round((price - prev.price) / prev.price * 100, 2)
                    if delta != 0:
                        price_changes.append({
                            "product_name": product.name,
                            "seller_name": seller.seller_name,
                            "delta_pct": delta,
                            "latest_price": price,
                        })

                db.add(PriceHistory(seller_id=seller.id, price=price))

        db.commit()

        # Notifications
        notif_settings = db.query(NotificationSettings).first()
        if notif_settings and price_changes:
            notify_if_needed(price_changes, {
                "email": notif_settings.email,
                "tg_chat_id": notif_settings.tg_chat_id,
                "threshold": notif_settings.threshold,
            })

    except Exception:
        db.rollback()
        logger.exception("Error during price update")
    finally:
        db.close()

    logger.info(f"Update complete: {len(price_changes)} price changes")


def cleanup_old_prices() -> None:
    """Delete price_history records older than 180 days."""
    from api.models import PriceHistory

    cutoff = datetime.utcnow() - timedelta(days=180)
    db = Session()
    try:
        deleted = db.query(PriceHistory).filter(PriceHistory.recorded_at < cutoff).delete()
        db.commit()
        logger.info(f"Cleanup: deleted {deleted} old records")
    finally:
        db.close()


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(update_all_prices, "interval", hours=3, next_run_time=datetime.utcnow())
    scheduler.add_job(cleanup_old_prices, "cron", hour=3, minute=0)
    logger.info("Scheduler started")
    scheduler.start()
