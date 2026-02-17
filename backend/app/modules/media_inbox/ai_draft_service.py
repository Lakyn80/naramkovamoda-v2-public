from __future__ import annotations

import os
from typing import Any

from app.modules.ai.drafts.service import build_draft_from_image
from app.modules.ai.pipeline.openai_vision import generate_openai_rag_description
from app.modules.ai.rag.service import detect_product_type


PIPELINE_OPENAI = "openai_vision"


def _is_openai_pipeline() -> bool:
    value = os.getenv("NMM_AI_PIPELINE") or os.getenv("AI_PIPELINE") or ""
    return value.strip().lower() == PIPELINE_OPENAI


def generate_draft_for_inbox_image(image_path: str) -> dict[str, Any]:
    if _is_openai_pipeline():
        result = generate_openai_rag_description(image_path)
        tags = list(result.tags or [])
        product_type = detect_product_type(tags) if tags else "other"
        return {
            "title": result.title,
            "description": result.description,
            "product_type": product_type,
            "combined_tags": tags,
        }
    return build_draft_from_image(image_path)
