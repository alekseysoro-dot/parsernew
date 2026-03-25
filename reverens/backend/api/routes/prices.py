from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import PriceHistory, Product, Seller
from api.schemas import DeltaSummary, PriceHistoryPoint, SellerPriceOut

router = APIRouter()


def _price_delta(old: int | None, new: int) -> float | None:
    if not old:
        return None
    return round((new - old) / old * 100, 2)


@router.get("/prices/{product_id}", response_model=list[SellerPriceOut])
def get_latest_prices(product_id: str, db: Session = Depends(get_db)):
    sellers = db.query(Seller).filter(Seller.product_id == product_id).all()
    result = []
    for seller in sellers:
        records = (
            db.query(PriceHistory)
            .filter(PriceHistory.seller_id == seller.id)
            .order_by(PriceHistory.recorded_at.desc())
            .limit(2)
            .all()
        )
        if not records:
            continue
        latest = records[0].price
        prev = records[1].price if len(records) > 1 else None
        result.append(
            SellerPriceOut(
                seller_name=seller.seller_name,
                seller_id=seller.seller_id,
                latest_price=latest,
                prev_price=prev,
                delta_pct=_price_delta(prev, latest),
            )
        )
    return result


@router.get("/prices/{product_id}/history", response_model=list[PriceHistoryPoint])
def get_price_history(
    product_id: str,
    days: int = Query(default=30, ge=1, le=180),
    db: Session = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    seller_ids = [
        s.id for s in db.query(Seller).filter(Seller.product_id == product_id).all()
    ]
    records = (
        db.query(PriceHistory, Seller.seller_name)
        .join(Seller)
        .filter(PriceHistory.seller_id.in_(seller_ids), PriceHistory.recorded_at >= since)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )
    return [
        PriceHistoryPoint(
            seller_name=seller_name,
            price=ph.price,
            recorded_at=ph.recorded_at,
        )
        for ph, seller_name in records
    ]


@router.get("/prices/{product_id}/delta", response_model=DeltaSummary)
def get_price_delta(product_id: str, db: Session = Depends(get_db)):
    sellers = db.query(Seller).filter(Seller.product_id == product_id).all()
    deltas = []
    seller_summary = []
    for seller in sellers:
        records = (
            db.query(PriceHistory)
            .filter(PriceHistory.seller_id == seller.id)
            .order_by(PriceHistory.recorded_at.desc())
            .limit(2)
            .all()
        )
        if len(records) < 2:
            continue
        delta = _price_delta(records[1].price, records[0].price)
        if delta is not None:
            deltas.append(delta)
            seller_summary.append({"seller_name": seller.seller_name, "delta_pct": delta})

    return DeltaSummary(
        min_delta=min(deltas) if deltas else None,
        max_delta=max(deltas) if deltas else None,
        avg_delta=round(sum(deltas) / len(deltas), 2) if deltas else None,
        sellers=seller_summary,
    )
