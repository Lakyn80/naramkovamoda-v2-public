from __future__ import annotations

import json
import logging
import os
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.text_sanitize import remove_banned_word_variants
from app.core.ai_config import get_openai_api_key
from app.modules.ai.rag.service import (
    build_required_structure_from_vision,
    detect_product_type,
    translate_tags_to_czech,
)
from app.modules.ai.templates.service import suggest_price
from app.modules.auth.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai/deepseek", tags=["ai-deepseek"], dependencies=[Depends(require_admin)])


class GenerateRequest(BaseModel):
    context: str


def _split_tags(raw: str) -> List[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _extract_tags_from_context(context: str) -> List[str]:
    tags: List[str] = []
    for line in (context or "").splitlines():
        low = line.lower().strip()
        if low.startswith("labels:"):
            tags.extend(_split_tags(line.split(":", 1)[1]))
            continue
        if low.startswith("objects:"):
            tags.extend(_split_tags(line.split(":", 1)[1]))
            continue
        if low.startswith("dominant colors:") or low.startswith("dominant_colors:") or low.startswith("colors:"):
            tags.extend(_split_tags(line.split(":", 1)[1]))
            continue
    return tags


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in (text or "").splitlines()]
    return "\n".join([line for line in lines if line]).strip()


def _extract_after_marker(context: str, marker: str) -> str:
    if not context:
        return ""
    low = context.lower()
    mark_low = marker.lower()
    idx = low.rfind(mark_low)
    if idx < 0:
        return ""
    return context[idx + len(marker) :].strip()


def _extract_description_payload(context: str) -> str:
    for label in ("current description:", "description:"):
        extracted = _extract_after_marker(context, label)
        if extracted:
            return extracted
    for marker in (
        "return plain text only.",
        "return bullet points only",
        "return only the numeric price.",
    ):
        extracted = _extract_after_marker(context, marker)
        if extracted:
            return extracted
    parts = [p.strip() for p in re.split(r"\n\s*\n", context or "") if p.strip()]
    if parts:
        return parts[-1]
    return (context or "").strip()


def _shorten_text(text: str) -> str:
    text = _normalize_text(text)
    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join([s.strip() for s in sentences if s.strip()][:2]).strip()
    if not short:
        short = text
    if len(short) > 240:
        short = short[:240].rsplit(" ", 1)[0].rstrip() + "…"
    return short


def _improve_tone(text: str) -> str:
    text = _normalize_text(text)
    if not text:
        return text
    if len(text) < 140:
        extra = "Působí jemně a doplní váš styl."
        if extra.lower() not in text.lower():
            text = f"{text} {extra}"
    return text


def _bullets_from_text(text: str, max_items: int = 6) -> List[str]:
    if not text:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullets = [re.sub(r"^[\-\–\•\*\s]+", "", line).strip() for line in lines if line.lstrip().startswith(("-", "•", "*"))]
    bullets = [b for b in bullets if b]
    if bullets:
        return bullets[:max_items]
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]
    bullets = [s for s in sentences if len(s.split()) >= 3][:max_items]
    if bullets:
        return bullets
    return ["Detailní provedení", "Jemné barevné tóny", "Příjemný doplněk"]


def _default_price_from_context(context: str, product_type: str) -> int:
    low = (context or "").lower()
    if "náramek" in low or product_type == "bracelet":
        return 299
    if "svíčka" in low or product_type == "candle":
        return 299
    if "náhrdelník" in low or product_type == "necklace":
        return 349
    if "náušnice" in low or product_type == "earrings":
        return 249
    if "dekorace" in low or product_type == "decor":
        return 399
    if "klíčenka" in low or product_type == "keychain":
        return 199
    if "samolepka" in low or product_type == "sticker":
        return 99
    if "poukaz" in low or product_type == "gift voucher":
        return 500
    if "kartička" in low or product_type == "gift card":
        return 100
    return 299


def _fallback_from_tags(context: str) -> tuple[str, str, str, List[str]]:
    raw_tags = _extract_tags_from_context(context)
    tags_cz = translate_tags_to_czech(raw_tags) if raw_tags else []
    product_type = detect_product_type(tags_cz)
    title, description = build_required_structure_from_vision(product_type, tags_cz)
    return title, description, product_type, tags_cz


def _fallback_generate(context: str) -> str:
    low = (context or "").lower()

    if "return json only with keys:" in low:
        is_variant = "variant_name" in low
        title, description, product_type, tags_cz = _fallback_from_tags(context)
        price = None
        try:
            price = suggest_price(product_type=product_type, combined_tags=tags_cz)
        except Exception:
            price = None
        if price is None:
            price = _default_price_from_context(context, product_type)
        payload = {
            ("variant_name" if is_variant else "name"): title,
            "description": description,
            "price_czk": int(price) if price is not None else _default_price_from_context(context, product_type),
            "stock": 1,
        }
        if not is_variant:
            payload["category_slug"] = ""
        return json.dumps(payload, ensure_ascii=False)

    if "suggest a czk price" in low or "suggest a czk price as a number" in low:
        desc = _extract_description_payload(context)
        match = re.search(r"\b(\d{2,5})(?:[.,]\d+)?\b", desc)
        if match:
            return match.group(1)
        _, _, product_type, tags_cz = _fallback_from_tags(context)
        price = None
        try:
            price = suggest_price(product_type=product_type, combined_tags=tags_cz)
        except Exception:
            price = None
        if price is None:
            price = _default_price_from_context(context, product_type)
        return str(int(price))

    if "generate 3-6 bullet" in low or "bullet highlights" in low:
        desc = _extract_description_payload(context)
        bullets = _bullets_from_text(desc)
        return "\n".join([f"- {b}" for b in bullets])

    if "shorten the following" in low:
        desc = _extract_description_payload(context)
        return _shorten_text(desc)

    if "rewrite the" in low and "description" in low:
        desc = _extract_description_payload(context)
        return _normalize_text(desc)

    if "vylepšit marketingový tón" in low or "improve" in low and "tone" in low:
        desc = _extract_description_payload(context)
        return _improve_tone(desc)

    if any(token in low for token in ("labels:", "dominant colors:", "dominant_colors:", "objects:")):
        _, description, _, _ = _fallback_from_tags(context)
        return description

    return _normalize_text(context)


@router.post("/generate")
def generate_text(payload: GenerateRequest) -> dict:
    context = (payload.context or "").strip()
    if not context:
        raise HTTPException(status_code=400, detail="Missing context")

    api_key = get_openai_api_key()
    if not api_key:
        fallback = _fallback_generate(context)
        return {"text": remove_banned_word_variants(fallback)}

    system_prompt = os.getenv(
        "NMM_TEXT_SYSTEM_PROMPT",
        os.getenv("OPENAI_SYSTEM_PROMPT", "You are a helpful assistant. Follow the user's instructions precisely."),
    )
    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
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
        if text:
            return {"text": remove_banned_word_variants(text)}
        raise ValueError("Empty response")
    except Exception as exc:
        logger.warning("OpenAI generation failed, using fallback. reason=%s", exc)
        fallback = _fallback_generate(context)
        return {"text": remove_banned_word_variants(fallback)}
