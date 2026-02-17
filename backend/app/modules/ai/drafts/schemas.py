from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DraftResponse(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    product_type: Optional[str] = None
    combined_tags: list[str] = []
    suggested_price_czk: Optional[float] = None
    suggested_variant_price_czk: Optional[float] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
