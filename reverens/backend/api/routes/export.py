import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import PriceHistory, Product, Seller

router = APIRouter()


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "wb_article", "wb_url", "group_name", "seller_name", "latest_price", "recorded_at"])

    for product in products:
        for seller in product.sellers:
            latest = (
                db.query(PriceHistory)
                .filter(PriceHistory.seller_id == seller.id)
                .order_by(PriceHistory.recorded_at.desc())
                .first()
            )
            writer.writerow([
                product.id,
                product.name,
                product.wb_article or "",
                product.wb_url,
                product.group_name or "",
                seller.seller_name,
                latest.price if latest else "",
                latest.recorded_at.isoformat() if latest else "",
            ])

    output.seek(0)
    filename = f"prices_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
