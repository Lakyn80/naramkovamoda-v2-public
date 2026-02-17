from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from .schemas import OrderClientCreateResponse, OrderCreateIn, OrderCreateResponse, OrderGetResponse
from .service import (
    create_order,
    create_order_client,
    get_order_by_id as get_order_by_id_service,
    get_order_by_vs as get_order_by_vs_service,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderCreateResponse, status_code=201)
async def create_order_endpoint(
    payload: Optional[OrderCreateIn] = Body(default=None),
    db: Session = Depends(get_db),
) -> OrderCreateResponse:
    """Legacy: POST /api/orders."""
    status_code, data = create_order(db, (payload or {}).model_dump() if payload else {})
    return JSONResponse(status_code=status_code, content=data)


@router.get("/{order_id}", response_model=OrderGetResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)) -> OrderGetResponse:
    """Legacy: GET /api/orders/<int:order_id>."""
    status_code, data = get_order_by_id_service(db=db, order_id=order_id)
    return JSONResponse(status_code=status_code, content=data)


@router.get("/by-vs/{vs}", response_model=OrderGetResponse)
async def get_order_by_vs(vs: str, db: Session = Depends(get_db)) -> OrderGetResponse:
    """Legacy: GET /api/orders/by-vs/<vs>."""
    status_code, data = get_order_by_vs_service(db=db, vs=vs)
    return JSONResponse(status_code=status_code, content=data)


@router.post("/client", response_model=OrderClientCreateResponse, status_code=201)
async def create_order_client_endpoint(
    payload: Optional[OrderCreateIn] = Body(default=None),
    db: Session = Depends(get_db),
) -> OrderClientCreateResponse:
    """Legacy: POST /api/orders/client (compat endpoint)."""
    status_code, data = create_order_client(db, (payload or {}).model_dump() if payload else {})
    return JSONResponse(status_code=status_code, content=data)
