"""Parse endpoints: search WB, write results to DB."""

import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.config import settings
from api.db import get_db
from api.models import Product, PriceHistory, Seller
from api.notifier import check_price_alerts
from api.schemas import ParseRunIn, ParseRunOut, ParseStatusOut
from api.wb_client import search_wb

router = APIRouter()

logger = logging.getLogger(__name__)

# In-memory storage for completed runs (frontend polls status after POST)
_active_runs: dict[str, dict] = {}


def _parse_price(raw) -> int | None:
    """Extract integer price from string '29 398 ₽' or pass through int."""
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


def _save_results(items: list[dict], db: Session) -> int:
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
            seller = Seller(
                product_id=product.id,
                seller_name=supplier_name,
                seller_id=supplier_name,
            )
            db.add(seller)
            db.flush()

        db.add(PriceHistory(seller_id=seller.id, price=price))
        written += 1

    db.commit()
    return written


@router.post("/parse/run", response_model=ParseRunOut)
async def run_parse(body: ParseRunIn = None, db: Session = Depends(get_db)):
    keyword = (body.keyword if body and body.keyword else None) or settings.apify_keyword
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword not provided and APIFY_KEYWORD not configured")

    try:
        items = await search_wb(keyword)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    updated = _save_results(items, db)

    try:
        alerts = check_price_alerts(db)
        if alerts:
            logger.info(f"Sent {alerts} price alert(s)")
    except Exception:
        logger.exception("Error checking price alerts")

    internal_id = str(uuid.uuid4())
    _active_runs[internal_id] = {"status": "SUCCEEDED", "updated": updated}

    return ParseRunOut(
        run_id=internal_id,
        status="RUNNING",
        total_products=db.query(Product).count(),
    )


@router.get("/parse/status/{run_id}", response_model=ParseStatusOut)
async def parse_status(run_id: str, db: Session = Depends(get_db)):
    run_info = _active_runs.pop(run_id, None)
    if not run_info:
        raise HTTPException(status_code=404, detail="Run not found")

    return ParseStatusOut(
        run_id=run_id,
        status=run_info["status"],
        updated=run_info.get("updated"),
        error=run_info.get("error"),
    )
