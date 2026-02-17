from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import require_admin
from .schemas import ProductCreateIn, ProductOut, ProductUpdateIn
from .service import create_product, delete_product, get_product, list_products, update_product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def list_products_endpoint(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    """Legacy: GET /api/products/."""
    return list_products(db, include_inactive=include_inactive)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product_endpoint(product_id: int, db: Session = Depends(get_db)) -> ProductOut:
    """Legacy: GET /api/products/<int:product_id>."""
    data = get_product(db, product_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data


@router.post("", response_model=ProductOut, status_code=201)
async def add_product(
    request: Request,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProductOut:
    """Legacy: POST /api/products/ (JSON or multipart)."""
    payload: dict[str, Any] = {}
    form_data: dict[str, Any] | None = None
    files: dict[str, list[Any]] | None = None

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        form_data = {}
        files = {}
        for key, value in form.multi_items():
            if hasattr(value, "filename"):
                files.setdefault(key, []).append(value)
            else:
                if key in form_data:
                    if isinstance(form_data[key], list):
                        form_data[key].append(value)
                    else:
                        form_data[key] = [form_data[key], value]
                else:
                    form_data[key] = value

    try:
        data = create_product(db, payload=payload, form=form_data, files=files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return data


@router.put("/{product_id}", response_model=ProductOut)
async def update_product_endpoint(
    product_id: int,
    request: Request,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProductOut:
    """Legacy: PUT /api/products/<int:product_id> (JSON or multipart)."""
    payload_dict: dict[str, Any] = {}
    form_data: dict[str, Any] | None = None
    files: dict[str, list[Any]] | None = None

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        raw = await request.json()
        payload_dict = ProductUpdateIn(**raw).dict(exclude_unset=True)
    elif "multipart/form-data" in content_type:
        form = await request.form()
        form_data = {}
        files = {}
        for key, value in form.multi_items():
            if hasattr(value, "filename"):
                files.setdefault(key, []).append(value)
            else:
                if key in form_data:
                    if isinstance(form_data[key], list):
                        form_data[key].append(value)
                    else:
                        form_data[key] = [form_data[key], value]
                else:
                    form_data[key] = value

    try:
        data = update_product(db, product_id=product_id, payload=payload_dict, form=form_data, files=files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data


@router.delete("/{product_id}")
async def delete_product_endpoint(
    product_id: int,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Legacy: DELETE /api/products/<int:product_id>."""
    success = delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}
