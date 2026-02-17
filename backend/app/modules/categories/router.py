from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import require_admin
from .schemas import CategoryCreateIn, CategoryOut, CategoryUpdateIn, CategoryWithProductsOut
from .service import (
    create_category,
    delete_category,
    get_category_by_id,
    get_category_by_slug,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories_endpoint(
    group: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CategoryOut]:
    """Legacy: GET /api/categories/ (optional filter by group/category query)."""
    group_val = group or category
    return list_categories(db, group_val)


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category_endpoint(category_id: int, db: Session = Depends(get_db)) -> CategoryOut:
    """Legacy: GET /api/categories/<int:category_id>."""
    data = get_category_by_id(db, category_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data


@router.get("/{slug}", response_model=CategoryWithProductsOut)
async def get_category_by_slug_endpoint(
    slug: str,
    wrist_size: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> CategoryWithProductsOut:
    """Legacy: GET /api/categories/<slug> (includes products list)."""
    data = get_category_by_slug(db, slug, wrist_size)
    if not data:
        return JSONResponse(status_code=404, content={"error": "Category not found"})
    return data


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category_endpoint(
    payload: Optional[CategoryCreateIn] = Body(default=None),
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoryOut:
    """Legacy: POST /api/categories/."""
    payload_dict = payload.dict(exclude_unset=True) if payload else {}
    try:
        return create_category(db, payload_dict)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category_endpoint(
    category_id: int,
    payload: Optional[CategoryUpdateIn] = Body(default=None),
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoryOut:
    """Legacy: PUT /api/categories/<int:category_id>."""
    payload_dict = payload.dict(exclude_unset=True) if payload else {}
    try:
        data = update_category(db, category_id, payload_dict)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data


@router.delete("/{category_id}")
async def delete_category_endpoint(
    category_id: int,
    force: bool = Query(default=False),
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Legacy: DELETE /api/categories/<int:category_id>."""
    ok, message = delete_category(db, category_id, force=force)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    if message:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True}
