from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from sqlalchemy.orm import Session, selectinload

from app.db.models import Category, Product, ProductVariant
from app.modules.products.service import _product_dict, delete_product


def _cat_to_dict(category: Category) -> dict[str, Any]:
    return {
        "id": category.id,
        "name": category.name,
        "description": getattr(category, "description", None),
        "slug": getattr(category, "slug", None),
        "group": getattr(category, "group", None),
        "category": getattr(category, "group", None),
    }


def _slugify(val: str) -> str:
    raw = (val or "").strip().lower()
    if not raw:
        return "kategorie"
    try:
        normalized = unicodedata.normalize("NFKD", raw)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    except Exception:
        normalized = raw
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "kategorie"


def _unique_slug(db: Session, base: str, exclude_id: int | None = None) -> str:
    slug = base or "kategorie"
    candidate = slug
    suffix = 1
    while True:
        q = db.query(Category).filter(Category.slug == candidate)
        if exclude_id:
            q = q.filter(Category.id != exclude_id)
        if not q.first():
            return candidate
        suffix += 1
        candidate = f"{slug}-{suffix}"


def list_categories(db: Session, group: Optional[str]) -> list[dict[str, Any]]:
    q = db.query(Category)
    if group:
        q = q.filter(Category.group == group)
    items = q.order_by(Category.name.asc()).all()
    return [_cat_to_dict(c) for c in items]


def get_category_by_id(db: Session, category_id: int) -> dict[str, Any] | None:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        return None
    return _cat_to_dict(cat)


def get_category_by_slug(db: Session, slug: str, wrist_size: Optional[str]) -> dict[str, Any] | None:
    cat = db.query(Category).filter(Category.slug == str(slug).strip()).first()
    if not cat:
        return None

    products_q = (
        db.query(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.category),
            selectinload(Product.variants).selectinload(ProductVariant.media),
        )
        .filter(Product.category_id == cat.id)
    )
    if hasattr(Product, "active"):
        products_q = products_q.filter(Product.active.is_(True))

    if wrist_size:
        products_q = (
            products_q.join(ProductVariant, ProductVariant.product_id == Product.id)
            .filter(ProductVariant.wrist_size == wrist_size)
            .distinct()
        )

    products = products_q.order_by(Product.id.desc()).all()

    return {
        "category": _cat_to_dict(cat),
        "products": [_product_dict(p) for p in products],
    }


def create_category(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip() or None
    group_val = (payload.get("group") or payload.get("category") or "").strip() or None
    slug_raw = (payload.get("slug") or "").strip()

    if not name:
        raise ValueError("Missing 'name'")

    slug_val = _unique_slug(db, _slugify(slug_raw or name))

    cat = Category(name=name, description=description, group=group_val, slug=slug_val)
    try:
        db.add(cat)
        db.commit()
        db.refresh(cat)
        return _cat_to_dict(cat)
    except Exception:
        db.rollback()
        raise


def update_category(db: Session, category_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        return None

    new_name: str | None = None
    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("Invalid 'name'")
        cat.name = name
        new_name = name

    if "description" in payload:
        cat.description = (payload.get("description") or "").strip() or None

    if "group" in payload or "category" in payload:
        cat.group = (payload.get("group") or payload.get("category") or "").strip() or None

    if "slug" in payload or (not getattr(cat, "slug", None) and new_name):
        slug_raw = (payload.get("slug") or "").strip()
        slug_source = slug_raw or new_name or cat.name
        cat.slug = _unique_slug(db, _slugify(slug_source), exclude_id=cat.id)

    try:
        db.commit()
        db.refresh(cat)
        return _cat_to_dict(cat)
    except Exception:
        db.rollback()
        raise


def delete_category(db: Session, category_id: int, *, force: bool) -> tuple[bool, str | None]:
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        return False, None

    products = (
        db.query(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.variants).selectinload(ProductVariant.media),
        )
        .filter(Product.category_id == category_id)
        .all()
    )

    if products and not force:
        return True, "Kategorie obsahuje produkty. Nejprve je odstraňte nebo potvrďte hromadné smazání."

    try:
        for product in products:
            delete_product(db, product.id, commit=False)
        db.delete(cat)
        db.commit()
        return True, None
    except Exception:
        db.rollback()
        raise
