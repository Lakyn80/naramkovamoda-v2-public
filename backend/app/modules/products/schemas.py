from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field




class ProductMediaOut(BaseModel):
    id: Optional[int] = None
    filename: Optional[str] = None
    media_type: Optional[str] = None
    url: Optional[str] = None


class ProductVariantMediaOut(BaseModel):
    id: Optional[int] = None
    image: Optional[str] = None
    image_url: Optional[str] = None
    image_full_url: Optional[str] = None
    image_thumb_url: Optional[str] = None


class ProductVariantOut(BaseModel):
    id: Optional[int] = None
    variant_name: Optional[str] = None
    wrist_size: Union[str, int, float, None] = None
    description: Optional[str] = None
    price_czk: Optional[float] = None
    stock: Optional[int] = None
    image: Optional[str] = None
    image_url: Optional[str] = None
    image_full_url: Optional[str] = None
    image_thumb_url: Optional[str] = None
    media: list[ProductVariantMediaOut] = Field(default_factory=list)


class ProductOut(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    active: Optional[bool] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    wrist_size: Union[str, int, float, None] = None
    image_url: Optional[str] = None
    image_full_url: Optional[str] = None
    image_thumb_url: Optional[str] = None
    media: list[str] = Field(default_factory=list)
    media_items: list[ProductMediaOut] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    category_group: Optional[str] = None
    variants: list[ProductVariantOut] = Field(default_factory=list)


class ProductVariantIn(BaseModel):
    variant_name: Optional[str] = None
    wrist_size: Union[str, int, float, None] = None
    description: Optional[str] = None
    price_czk: Optional[float] = None
    stock: Optional[int] = None
    image: Optional[str] = None


class ProductCreateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    price: Optional[float] = None
    price_czk: Optional[float] = None
    stock: Optional[int] = None
    active: Optional[bool] = None
    category_id: Optional[int] = None
    wrist_size: Union[str, int, float, None] = None
    wrist_sizes: Optional[str] = None
    variants: Optional[list[ProductVariantIn]] = None


class ProductUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    price: Optional[float] = None
    price_czk: Optional[float] = None
    stock: Optional[int] = None
    active: Optional[bool] = None
    category_id: Optional[int] = None
    wrist_size: Union[str, int, float, None] = None
    wrist_sizes: Optional[str] = None
    variants: Optional[list[ProductVariantIn]] = None
