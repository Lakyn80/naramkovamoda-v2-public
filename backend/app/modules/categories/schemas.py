from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.modules.products.schemas import ProductOut


class CategoryOut(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    slug: Optional[str] = None
    group: Optional[str] = None
    category: Optional[str] = None


class CategoryWithProductsOut(BaseModel):
    category: CategoryOut = Field(default_factory=CategoryOut)
    products: list[ProductOut] = Field(default_factory=list)


class CategoryCreateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None


class CategoryUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None
