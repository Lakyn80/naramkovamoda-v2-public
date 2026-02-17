from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session, selectinload

from app.db.models import Product
from app.db.session import get_db

from .service import build_gmc_feed

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


@router.get("/gmc.xml")
def gmc_feed(db: Session = Depends(get_db)) -> Response:
    products = (
        db.query(Product)
        .options(selectinload(Product.variants))
        .order_by(Product.id.desc())
        .all()
    )
    xml = build_gmc_feed(products)
    return Response(content=xml, media_type="application/xml")
