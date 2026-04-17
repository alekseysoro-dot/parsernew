"""Keywords CRUD: manage search keywords for WB parsing."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import Keyword, Product, Seller, PriceHistory
from api.schemas import KeywordCreate, KeywordOut

router = APIRouter()


@router.get("/keywords", response_model=list[KeywordOut])
def list_keywords(db: Session = Depends(get_db)):
    return db.query(Keyword).order_by(Keyword.created_at.desc()).all()


@router.post("/keywords", response_model=KeywordOut, status_code=201)
def create_keyword(body: KeywordCreate, db: Session = Depends(get_db)):
    if not body.keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword must not be empty")

    kw = Keyword(keyword=body.keyword.strip(), category=body.category)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


@router.delete("/keywords/{keyword_id}", status_code=204)
def delete_keyword(keyword_id: str, db: Session = Depends(get_db)):
    kw = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Cascade delete products with matching category
    if kw.category:
        products = db.query(Product).filter(Product.group_name == kw.category).all()
        for product in products:
            db.query(PriceHistory).filter(
                PriceHistory.seller_id.in_(
                    db.query(Seller.id).filter(Seller.product_id == product.id)
                )
            ).delete(synchronize_session=False)
            db.query(Seller).filter(Seller.product_id == product.id).delete(synchronize_session=False)
            db.delete(product)

    db.delete(kw)
    db.commit()


@router.patch("/keywords/{keyword_id}", response_model=KeywordOut)
def toggle_keyword(keyword_id: str, db: Session = Depends(get_db)):
    kw = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    kw.is_active = not kw.is_active
    db.commit()
    db.refresh(kw)
    return kw
