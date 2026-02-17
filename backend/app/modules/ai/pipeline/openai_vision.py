from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from app.core.ai_config import get_openai_api_key
from app.core.text_sanitize import remove_banned_word_variants
from app.modules.ai.openai_vision.schemas import OpenAIVisionResult
from app.modules.ai.rag.service import (
    detect_product_type,
    get_best_rag_template,
    _inject_emojis_into_description,
    get_emoji_rotation_index,
    get_rag_title_pairs,
    translate_tags_to_czech,
)

logger = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = """
Z obrázku vrať pouze JSON ve tvaru:
{
  "vision_tags": ["..."],
  "vision_summary": "krátký popis toho, co je na obrázku"
}

Pravidla:
- Tags musí být krátké, česky, maximálně 12 položek.
- Vision_summary musí být stručné, faktické, bez marketingu.
- Nevymýšlej fakta, jen to, co je vidět na obrázku.
- Nevypisuj nic mimo JSON.
"""

GENERATION_SYSTEM_PROMPT = """
Jsi profesionální copywriter pro e-shop s ručními výrobky.
Vision je hlavní zdroj faktů.
RAG vzor je POVINNÁ šablona struktury a tónu.

VÝSTUP MUSÍ BÝT VŽDY v tomto formátu:
<NÁZEV S EMOJI – stručný a smysluplný>

✨ Popis produktu:
- 3–5 konkrétních bodů vycházejících z obrázku

💎 Styl: 2–3 přívlastky

Nepoužívej angličtinu ani prázdné marketingové fráze.
"""

BRACELET_TITLE_SYSTEM = """Jsi copywriter pro e-shop s ručními šperky.
Dostaneš popis obrázku a vzorové názvy z katalogu (dvouslovné + emoji).
Úkol: Vytvoř JEDEN originální dvouslovný název, který vychází z obrázku a je v duchu vzorů.
Formát výstupu: přesně „Slovo1 Slovo2“ a za to 1–3 vhodná emoji (např. 🐾 ✨ ⚫).
Pravidla: pouze dvě slova v uvozovkách „ “, žádné slovo „náramek“, žádný popis. Odpověz jen tímto názvem."""


def _generate_bracelet_title_with_openai(
    vision_summary: str,
    tags: list[str],
    rag_pairs: list[tuple[str, str]],
    model: str,
) -> str:
    """OpenAI vytvoří jeden dvouslovný název + emoji z obrázku a RAG vzorů."""
    examples = []
    for a, b in (rag_pairs or [])[:8]:
        if a and b:
            examples.append(f"„{a} {b}“")
    examples_str = ", ".join(examples) if examples else "např. „Psí harmonie“, „Křišťálový psík“"
    user = (
        f"Popis obrázku: {vision_summary}\n"
        f"Tagy: {', '.join(tags[:15]) if tags else '—'}\n\n"
        f"Vzorové názvy z katalogu: {examples_str}\n\n"
        "Vytvoř jeden originální název ve formátu „Slovo1 Slovo2“ + emoji."
    )
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": BRACELET_TITLE_SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    raw = _extract_text_from_response(response).strip()
    if not raw:
        return ""
    # Normalizace: ponech „ “ a emoji na konci
    raw = raw.strip().rstrip(".")
    # Ujisti se o správné uvozovky „ “
    if raw and raw[0] not in ("„", '"', "'"):
        raw = "„" + raw
    return raw[:120].strip()


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
                    block_type = getattr(block, "type", None) or (
                        block.get("type") if isinstance(block, dict) else None
                    )
                    if block_type in ("output_text", "text"):
                        block_text = getattr(block, "text", None) or (
                            block.get("text") if isinstance(block, dict) else ""
                        )
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


def _extract_vision_facts(image_path: str, model: str) -> tuple[list[str], str]:
    data_url = _image_to_data_url(image_path)
    api_key = get_openai_api_key()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
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
    if not isinstance(payload, dict):
        raise ValueError("OpenAI vision returned non-JSON output")

    tags_raw = payload.get("vision_tags") or []
    if not isinstance(tags_raw, list):
        tags_raw = []
    tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
    summary = str(payload.get("vision_summary") or "").strip()

    if not tags and not summary:
        raise ValueError("OpenAI vision returned empty output")

    return tags, summary


def _parse_generated_output(text: str) -> tuple[str, str]:
    if not text:
        raise ValueError("OpenAI returned empty output")
    lines = [line.rstrip() for line in text.splitlines()]
    first_idx = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_idx = idx
            break
    if first_idx is None:
        raise ValueError("OpenAI returned no title")
    title = lines[first_idx].strip()
    description = "\n".join(lines[first_idx + 1 :]).strip()
    if not description:
        # Accept single-block output to avoid falling back when structure is looser.
        description = text.strip()
    return title, description


def generate_openai_rag_description(
    image_path: str,
    model: str = "gpt-4.1",
) -> OpenAIVisionResult:
    tags: list[str] = []
    summary = ""
    output_text = ""
    product_type = "other"
    tags_cz: list[str] = []
    try:
        tags, summary = _extract_vision_facts(image_path, model)
        tags_cz = translate_tags_to_czech(tags)
        product_type = detect_product_type(tags_cz)
    except Exception as exc:
        logger.error("OpenAI Vision facts failed (no fallback): %s", exc)
        return OpenAIVisionResult(
            title="",
            description="",
            tags=[],
            model=model,
        )

    try:
        best_template = get_best_rag_template(tags, require_structure=False)
        user_prompt = (
            "A) VISION FAKTA:\n"
            f"{summary}\n"
            f"Tagy: {', '.join(tags)}\n\n"
            "B) JEDEN RAG VZOR (pokud existuje):\n"
            "---\n"
            f"{best_template}\n"
            "---"
        )

        api_key = get_openai_api_key()
        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        output_text = _extract_text_from_response(response)
        title, description = _parse_generated_output(output_text)
        rotation_index = get_emoji_rotation_index()
        if product_type == "bracelet":
            rag_pairs = get_rag_title_pairs(tags_cz or tags, product_type, n_results=8)
            try:
                openai_title = _generate_bracelet_title_with_openai(
                    vision_summary=summary,
                    tags=tags_cz or tags,
                    rag_pairs=rag_pairs,
                    model=model,
                )
                if openai_title:
                    title = openai_title
            except Exception as e:  # noqa: BLE001
                logger.warning("OpenAI bracelet title generation failed, using parsed title: %s", e)
        description = remove_banned_word_variants(description)
        description = _inject_emojis_into_description(description, tags_cz or tags, rotation_index=rotation_index)
        return OpenAIVisionResult(
            title=title,
            description=description,
            tags=tags_cz or tags,
            model=model,
        )
    except Exception as exc:
        snippet = (output_text or "").replace("\n", " ").strip()[:200]
        logger.error(
            "OpenAI Vision generation failed (no fallback). reason=%s output_snippet=%s",
            exc,
            snippet,
        )
        if output_text:
            try:
                title, description = _parse_generated_output(output_text)
            except Exception:
                title, description = "", output_text.strip()
        else:
            title, description = "", ""
        rotation_index = get_emoji_rotation_index()
        if product_type == "bracelet":
            rag_pairs = get_rag_title_pairs(tags_cz or tags, product_type, n_results=8)
            try:
                openai_title = _generate_bracelet_title_with_openai(
                    vision_summary=summary,
                    tags=tags_cz or tags,
                    rag_pairs=rag_pairs,
                    model=model,
                )
                if openai_title:
                    title = openai_title
            except Exception as e:  # noqa: BLE001
                logger.warning("OpenAI bracelet title (fallback) failed: %s", e)
        description = remove_banned_word_variants(description)
        description = _inject_emojis_into_description(description, tags_cz or tags, rotation_index=rotation_index)
        return OpenAIVisionResult(
            title=title,
            description=description,
            tags=tags_cz or tags,
            model=model,
        )
