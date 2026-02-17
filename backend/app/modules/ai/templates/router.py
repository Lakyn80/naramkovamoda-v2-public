from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import require_admin

from .schemas import TemplateListResponse, TemplateStoreRequest
from .service import list_template_items, store_template_for_product

router = APIRouter(prefix="/api/ai/templates", tags=["ai-templates"], dependencies=[Depends(require_admin)])


@router.post("/store")
def store_template(payload: TemplateStoreRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return store_template_for_product(db, payload.product_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/list", response_model=TemplateListResponse)
def list_templates() -> TemplateListResponse:
    items = list_template_items()
    return TemplateListResponse(items=items)
