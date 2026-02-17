from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import require_admin
from .schemas import (
    DeleteOrderResponse,
    MarkPaidRequest,
    MarkPaidResponse,
    PaymentListResponse,
    PaymentQrPayloadResponse,
    PaymentStatusByVsResponse,
    PaymentSummaryResponse,
    SyncCsobMailResponse,
    SyncFromOrdersResponse,
    UpdatePaymentStatusRequest,
    UpdatePaymentStatusResponse,
)
from .service import (
    delete_order_with_relations,
    get_status_by_vs,
    mark_paid_by_vs,
    payment_qr_payload,
    payment_qr_png,
    payments_list,
    payments_summary,
    sync_csob_mail,
    sync_from_orders,
    update_payment_status,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/qr")
async def payment_qr_png_endpoint(
    amount: Optional[str] = Query(default=None),
    vs: Optional[str] = Query(default=None),
    msg: Optional[str] = Query(default=None),
) -> Response:
    """Legacy: GET /api/payments/qr (PNG)."""
    status_code, data, headers = payment_qr_png(amount, vs, msg)
    if isinstance(data, (bytes, bytearray)):
        return Response(content=data, media_type="image/png", status_code=status_code, headers=headers)
    return JSONResponse(status_code=status_code, content=data)


@router.get("/qr/payload", response_model=PaymentQrPayloadResponse)
async def payment_qr_payload_endpoint(
    amount: Optional[str] = Query(default=None),
    vs: Optional[str] = Query(default=None),
    msg: Optional[str] = Query(default=None),
) -> PaymentQrPayloadResponse:
    """Legacy: GET /api/payments/qr/payload."""
    status_code, data = payment_qr_payload(amount, vs, msg)
    return JSONResponse(status_code=status_code, content=data)


@router.get("/summary", response_model=PaymentSummaryResponse)
async def payments_summary_endpoint(
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentSummaryResponse:
    """Legacy: GET /api/payments/summary."""
    status_code, data = payments_summary(db)
    return JSONResponse(status_code=status_code, content=data)


@router.get("", response_model=PaymentListResponse)
async def payments_list_endpoint(
    page: Optional[int] = Query(default=None),
    per_page: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    direction: Optional[str] = Query(default=None),
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentListResponse:
    """Legacy: GET /api/payments."""
    params = {
        "page": page,
        "per_page": per_page,
        "status": status,
        "sort": sort,
        "direction": direction,
    }
    status_code, data = payments_list(db, params)
    return JSONResponse(status_code=status_code, content=data)


@router.post("/mark-paid", response_model=MarkPaidResponse)
async def mark_paid_by_vs_endpoint(
    payload: Optional[MarkPaidRequest] = Body(default=None),
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MarkPaidResponse:
    """Legacy: POST /api/payments/mark-paid."""
    status_code, data = mark_paid_by_vs(db, (payload or {}).model_dump() if payload else {})
    return JSONResponse(status_code=status_code, content=data)


@router.post("/update-status", response_model=UpdatePaymentStatusResponse)
async def update_payment_status_endpoint(
    payload: Optional[UpdatePaymentStatusRequest] = Body(default=None),
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UpdatePaymentStatusResponse:
    """Legacy: POST /api/payments/update-status."""
    status_code, data = update_payment_status(db, (payload or {}).model_dump() if payload else {})
    return JSONResponse(status_code=status_code, content=data)


@router.delete("/order/{order_id}", response_model=DeleteOrderResponse)
async def delete_order_endpoint(
    order_id: int,
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DeleteOrderResponse:
    """Admin: DELETE /api/payments/order/<order_id>."""
    status_code, data = delete_order_with_relations(db, order_id)
    return JSONResponse(status_code=status_code, content=data)


@router.post("/sync-from-orders", response_model=SyncFromOrdersResponse)
async def sync_from_orders_endpoint(
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SyncFromOrdersResponse:
    """Legacy: POST /api/payments/sync-from-orders."""
    status_code, data = sync_from_orders(db)
    return JSONResponse(status_code=status_code, content=data)


@router.get("/status/by-vs/{vs}", response_model=PaymentStatusByVsResponse)
async def get_status_by_vs_endpoint(
    vs: str,
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaymentStatusByVsResponse:
    """Legacy: GET /api/payments/status/by-vs/<vs>."""
    status_code, data = get_status_by_vs(db, vs)
    return JSONResponse(status_code=status_code, content=data)


@router.post("/sync-csob-mail", response_model=SyncCsobMailResponse)
async def sync_csob_mail_endpoint(
    payload: Optional[dict[str, Any]] = Body(default=None),
    _admin: Any = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SyncCsobMailResponse:
    """Legacy: POST /api/payments/sync-csob-mail."""
    status_code, data = sync_csob_mail(db, payload or {})
    return JSONResponse(status_code=status_code, content=data)
