from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    variantId: Optional[int] = None


class OrderCreateIn(BaseModel):
    vs: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    note: Optional[str] = None
    items: list[OrderItemIn] = Field(default_factory=list)
    totalCzk: Optional[float] = None
    shippingCzk: Optional[float] = None
    shippingMode: Optional[str] = None


class OrderItemOut(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    subtotal: Optional[float] = None


class OrderOut(BaseModel):
    id: Optional[int] = None
    vs: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    note: Optional[str] = None
    totalCzk: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    items: list[OrderItemOut] = Field(default_factory=list)


class OrderGetResponse(BaseModel):
    ok: bool = True
    order: OrderOut = Field(default_factory=OrderOut)


class OrderCreateResponse(BaseModel):
    ok: bool = True
    orderId: Optional[int] = None
    vs: Optional[str] = None
    status: Optional[str] = None
    decremented_items: list[dict] = Field(default_factory=list)


class OrderClientCreateResponse(BaseModel):
    ok: bool = True
    orderId: Optional[int] = None
    vs: Optional[str] = None
    status: Optional[str] = None
    decremented_items: list[dict] = Field(default_factory=list)
