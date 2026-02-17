from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.modules.ai.pipeline.openai_vision import _extract_vision_facts
from app.modules.ai.rag.vision_client import analyze_image_with_vision
from app.modules.auth.deps import require_admin

router = APIRouter(prefix="/api/ai/vision", tags=["ai-vision"], dependencies=[Depends(require_admin)])

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


@router.post("/analyze")
async def analyze_image(image: UploadFile = File(...)) -> dict:
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="Missing image")
    temp_path = _save_upload_to_temp(image)
    try:
        if _is_openai_pipeline():
            model = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1")
            tags, summary = _extract_vision_facts(temp_path, model=model)
            return {
                "labels": tags,
                "scores": [],
                "objects": [],
                "web_entities": [],
                "text": summary,
            }
        return analyze_image_with_vision(temp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

