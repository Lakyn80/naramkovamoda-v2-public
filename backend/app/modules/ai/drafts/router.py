from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

import app.core.paths as core_paths
from app.db.models import Product, ProductVariant
from app.db.session import get_db
from app.modules.auth.deps import require_admin

from .schemas import DraftResponse
from .service import build_draft_from_image
from app.modules.ai.openai_vision.schemas import OpenAIVisionResult
from app.modules.ai.pipeline.openai_vision import generate_openai_rag_description

router = APIRouter(prefix="/api/ai", tags=["ai-drafts"], dependencies=[Depends(require_admin)])


PIPELINE_OPENAI = "openai_vision"


def _is_openai_pipeline() -> bool:
    value = os.getenv("NMM_AI_PIPELINE") or os.getenv("AI_PIPELINE") or ""
    normalized = value.strip().lower()
    return normalized in (PIPELINE_OPENAI, "openai-vision", "openai", "oai")


def _save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            tmp.write(chunk)
        return tmp.name


def _resolve_image_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = str(value).replace("\\", "/")
    if path.startswith("/static/uploads/"):
        path = path[len("/static/uploads/") :]
    if path.startswith("static/uploads/"):
        path = path[len("static/uploads/") :]
    while path.startswith("uploads/"):
        path = path[len("uploads/") :]
    path = path.lstrip("/")
    abs_path = Path(path)
    if abs_path.is_absolute():
        return abs_path if abs_path.exists() else None
    abs_path = core_paths.UPLOAD_DIR / path
    return abs_path if abs_path.exists() else None


@router.post("/products/{product_id}/draft", response_model=DraftResponse)
def draft_product(product_id: int, db: Session = Depends(get_db)) -> DraftResponse:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.image:
        raise HTTPException(status_code=404, detail="Product image not found")
    abs_path = _resolve_image_path(product.image)
    if not abs_path:
        raise HTTPException(status_code=404, detail="Image file not found")
    draft = build_draft_from_image(str(abs_path))
    return DraftResponse(**draft)


@router.post("/variants/{variant_id}/draft", response_model=DraftResponse)
def draft_variant(variant_id: int, db: Session = Depends(get_db)) -> DraftResponse:
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant or not variant.image:
        raise HTTPException(status_code=404, detail="Variant image not found")
    abs_path = _resolve_image_path(variant.image)
    if not abs_path:
        raise HTTPException(status_code=404, detail="Image file not found")
    draft = build_draft_from_image(str(abs_path))
    suggested = draft.pop("suggested_price_czk", None)
    draft["suggested_variant_price_czk"] = suggested
    return DraftResponse(**draft)


@router.post("/drafts/from-upload", response_model=OpenAIVisionResult | DraftResponse)
async def draft_from_upload(image: UploadFile = File(...)) -> OpenAIVisionResult | DraftResponse:
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="Missing image")
    temp_path = _save_upload_to_temp(image)
    try:
        if _is_openai_pipeline():
            return generate_openai_rag_description(temp_path)
        draft = build_draft_from_image(temp_path)
        return DraftResponse(**draft)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass
