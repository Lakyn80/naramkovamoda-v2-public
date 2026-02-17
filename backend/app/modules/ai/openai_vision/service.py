from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from app.core.ai_config import get_openai_api_key
from app.core.text_sanitize import remove_banned_word_variants
from .schemas import OpenAIVisionResult


SYSTEM_PROMPT = """
Vygeneruj e-shopový název a popis produktu v češtině POUZE podle obrázku.
Dodrž přesně tento formát (včetně emoji a nadpisů):

<NÁZEV S EMOJI – smysluplný, bez generických frází>

✨ Popis produktu:
- (3–5 konkrétních bodů odvozených z toho, co je na obrázku)

💎 Styl: (2–3 přívlastky, bez vět)

ZAKÁZÁNO: prázdné marketingové fráze typu 
„stylový produkt“, „vhodné jako dárek“, „moderní a elegantní“, 
„produkt vysoké kvality“, „ručně vyráběné/ruční tvorba“.

Navíc vrať JSON:
{ "title": "...", "description": "...", "tags": ["..."] }
kde tags jsou krátké a česky (max 12).
"""


def _image_to_data_url(image_path: str) -> str:
    mime, _ = mimetypes.guess_type(image_path)
    if not mime:
        mime = "image/jpeg"
    data = Path(image_path).read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _extract_text_from_response(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text)
    output = getattr(response, "output", None)
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            content = getattr(item, "content", None)
            if content is None and isinstance(item, dict):
                content = item.get("content")
            if isinstance(content, list):
                for block in content:
                    block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
                    if block_type in ("output_text", "text"):
                        block_text = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "")
                        if block_text:
                            parts.append(str(block_text))
        if parts:
            return "\n".join(parts).strip()
    try:
        return str(response)
    except Exception:
        return ""


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def analyze_image_openai(image_path: str, model: str = "gpt-4.1-mini") -> OpenAIVisionResult:
    data_url = _image_to_data_url(image_path)
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Analyzuj obrázek."},
                    {"type": "input_image", "image_url": data_url},
                ],
            },
        ],
    )

    raw_text = _extract_text_from_response(response)
    payload = _extract_json(raw_text)

    if isinstance(payload, dict):
        title = str(payload.get("title") or "")
        description = remove_banned_word_variants(str(payload.get("description") or ""))
        tags_raw = payload.get("tags") or []
        if not isinstance(tags_raw, list):
            tags_raw = []
        tags = [str(t) for t in tags_raw if t is not None]
        return OpenAIVisionResult(
            title=title,
            description=description,
            tags=tags,
            model=model,
        )

    return OpenAIVisionResult(
        title="",
        description=remove_banned_word_variants(raw_text or ""),
        tags=[],
        model=model,
    )
