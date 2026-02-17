from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.text_sanitize import remove_banned_word_variants
from app.modules.ai.rag.service import (
    build_required_structure_from_vision,
    detect_product_type,
    translate_tags_to_czech,
)
from app.modules.ai.rag.vision_client import analyze_image_with_vision, normalize_tags
from .schemas import OpenAIVisionResult
from .service import analyze_image_openai
from app.modules.auth.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/openai-vision", tags=["ai-openai-vision"], dependencies=[Depends(require_admin)])


def _save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            tmp.write(chunk)
        return tmp.name


@router.post("/analyze", response_model=OpenAIVisionResult)
async def analyze_openai_vision(image: UploadFile = File(...)) -> OpenAIVisionResult:
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="Missing image")
    temp_path = _save_upload_to_temp(image)
    try:
        return analyze_image_openai(temp_path)
    except Exception as exc:
        logger.warning("OpenAI vision analyze failed, using fallback. reason=%s", exc)
        try:
            vision_result = analyze_image_with_vision(temp_path)
            raw_tags = normalize_tags(vision_result)
            tags_cz = translate_tags_to_czech(raw_tags)
            product_type = detect_product_type(tags_cz)
            title, description = build_required_structure_from_vision(product_type, tags_cz)
            return OpenAIVisionResult(
                title=title,
                description=remove_banned_word_variants(description),
                tags=tags_cz,
                model="fallback",
            )
        except Exception as fallback_exc:
            raise HTTPException(status_code=500, detail=str(fallback_exc)) from fallback_exc
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass
