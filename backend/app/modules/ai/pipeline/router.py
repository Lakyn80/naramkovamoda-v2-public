from __future__ import annotations

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai import OpenAI

from app.core.ai_config import get_openai_api_key
from app.core.text_sanitize import remove_banned_word_variants
from app.modules.ai.drafts.service import build_draft_from_image
from app.modules.ai.openai_vision.schemas import OpenAIVisionResult
from app.modules.ai.pipeline.openai_vision import generate_openai_rag_description
from app.modules.auth.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai-pipeline"], dependencies=[Depends(require_admin)])


PIPELINE_OPENAI = "openai_vision"


def _save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            tmp.write(chunk)
        return tmp.name


def _normalize_pipeline(value: str | None) -> str:
    if not value:
        return PIPELINE_OPENAI
    normalized = value.strip().lower()
    if normalized in ("openai", "openai_vision", "openai-vision", "oai"):
        return PIPELINE_OPENAI
    return PIPELINE_OPENAI


def _get_pipeline() -> str:
    return _normalize_pipeline(os.getenv("NMM_AI_PIPELINE") or os.getenv("AI_PIPELINE"))


def _get_text_system_prompt() -> str:
    return (
        os.getenv("NMM_TEXT_SYSTEM_PROMPT")
        or os.getenv("OPENAI_SYSTEM_PROMPT")
        or "You are a helpful assistant. Follow the user's instructions precisely."
    )


def _generate_text_openai(context: str, system_prompt: str) -> str:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ],
        temperature=0.6,
        max_tokens=800,
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Empty response")
    return remove_banned_word_variants(text)


@router.post("/describe", response_model=OpenAIVisionResult | dict)
async def describe_from_upload(
    image: UploadFile | None = File(None),
    context: str | None = Form(None),
) -> OpenAIVisionResult | dict:
    if image and image.filename:
        temp_path = _save_upload_to_temp(image)
        try:
            pipeline = _get_pipeline()
            if pipeline == PIPELINE_OPENAI:
                try:
                    return generate_openai_rag_description(temp_path)
                except Exception as exc:
                    logger.error("OpenAI vision pipeline failed. reason=%s", exc)
                    raise HTTPException(status_code=502, detail="OpenAI pipeline failed") from exc
            draft = build_draft_from_image(temp_path)
            tags_raw = draft.get("combined_tags") or []
            if not isinstance(tags_raw, list):
                tags_raw = []
            tags = [str(tag) for tag in tags_raw if tag is not None]
            return OpenAIVisionResult(
                title=str(draft.get("title") or ""),
                description=remove_banned_word_variants(str(draft.get("description") or "")),
                tags=tags,
                model=PIPELINE_OPENAI,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    if context and context.strip():
        system_prompt = _get_text_system_prompt()
        try:
            text = _generate_text_openai(context, system_prompt)
        except Exception as exc:
            logger.error("Pipeline text generation failed. reason=%s", exc)
            raise HTTPException(status_code=502, detail="Text pipeline failed") from exc
        return {"text": remove_banned_word_variants(text)}

    raise HTTPException(status_code=400, detail="Missing image or context")
