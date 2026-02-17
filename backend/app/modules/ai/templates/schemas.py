from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TemplateStoreRequest(BaseModel):
    product_id: int


class TemplateItem(BaseModel):
    id: str
    product_id: Optional[int] = None
    title: Optional[str] = None
    product_type: Optional[str] = None
    price_czk: Optional[float] = None
    created_at: Optional[str] = None


class TemplateListResponse(BaseModel):
    items: list[TemplateItem]
