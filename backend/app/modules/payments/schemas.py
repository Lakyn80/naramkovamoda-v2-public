from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PaymentSummaryItem(BaseModel):
    id: Optional[int] = None
    vs: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    received_at: Optional[str] = None


class PaymentSummaryResponse(BaseModel):
    ok: bool = True
    source_table: Optional[str] = None
    count: Optional[int] = None
    sample: list[PaymentSummaryItem] = Field(default_factory=list)
    columns_present: list[str] = Field(default_factory=list)


class PaymentListResponse(BaseModel):
    ok: bool = True
    source_table: Optional[str] = None
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: Optional[int] = None
    items: list[PaymentSummaryItem] = Field(default_factory=list)
    sort: Optional[dict] = None


class PaymentQrPayloadResponse(BaseModel):
    ok: bool = True
    iban: Optional[str] = None
    amount: Optional[float] = None
    payload: Optional[str] = None


class PaymentStatusByVsResponse(BaseModel):
    ok: bool = True
    payment: Optional[dict] = None
    order: Optional[dict] = None


class MarkPaidRequest(BaseModel):
    vs: Optional[str] = None
    amountCzk: Optional[float] = None
    reference: Optional[str] = None


class MarkPaidResponse(BaseModel):
    ok: bool = True
    created: Optional[bool] = None
    paymentId: Optional[int] = None
    orderId: Optional[int] = None
    status: Optional[str] = None


class UpdatePaymentStatusRequest(BaseModel):
    order_id: Optional[int] = None
    payment_id: Optional[int] = None
    vs: Optional[str] = None
    status: Optional[str] = None


class UpdatePaymentStatusResponse(BaseModel):
    ok: bool = True
    orderId: Optional[int] = None
    status: Optional[str] = None
    sold_rows_created: Optional[int] = None
    emailed: Optional[bool] = None


class DeleteOrderResponse(BaseModel):
    ok: bool = True
    orderId: Optional[int] = None
    deleted_order: Optional[bool] = None
    deleted_payments: Optional[int] = None
    deleted_sold_rows: Optional[int] = None
    restocked_items: Optional[int] = None


class SyncFromOrdersResponse(BaseModel):
    ok: bool = True
    created: Optional[int] = None


class SyncCsobMailResponse(BaseModel):
    ok: bool = True
    shipping_fee_czk: Optional[float] = None
    matched: list[dict] = Field(default_factory=list)
    unmatched: list[dict] = Field(default_factory=list)
    diagnostic_self: list[dict] = Field(default_factory=list)
