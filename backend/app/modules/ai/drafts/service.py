# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any

from app.core.text_sanitize import remove_banned_word_variants
from app.modules.ai.rag.service import (
    _contains_emoji,
    _get_title_and_description,
    _inject_emojis_into_description,
    build_required_structure_from_vision,
    detect_product_type,
    format_bracelet_name_from_image,
    get_emoji_rotation_index,
    get_rag_title_pairs,
    get_best_rag_template,
    random_emoji,
    translate_tags_to_czech,
)
from app.modules.ai.rag.llm_client import _contains_banned_phrases, _has_required_structure
from app.modules.ai.rag.vision_client import analyze_image_with_vision, normalize_tags
from app.modules.ai.templates.service import suggest_price, load_ai_template_from_db


def _strip_emoji(text: str) -> str:
    if not text:
        return text
    return re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", text).strip()


def _truncate(text: str, max_len: int) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _build_seo_fields(title: str, description: str, tags: list[str]) -> dict[str, Any]:
    clean_title = _strip_emoji(title)
    clean_desc = " ".join((description or "").replace("\n", " ").split())
    seo_title = _truncate(clean_title or title, 60)
    seo_description = _truncate(clean_desc, 155)
    seo_keywords = ", ".join(tags[:10]) if tags else None
    return {
        "seo_title": seo_title or None,
        "seo_description": seo_description or None,
        "seo_keywords": seo_keywords or None,
    }


_ENGLISH_WORDS = {
    "a", "an", "the", "and", "or", "with", "for", "from", "of", "in", "on", "to",
    "this", "that", "these", "those", "is", "are", "was", "were", "be", "been",
    "your", "our", "their", "its", "it", "you", "we", "they",
    "handmade", "handcrafted", "crafted", "product", "description", "style",
    "materials", "material", "made", "natural", "bracelet", "bead", "beads",
    "gem", "gems", "gemstone", "stone", "stones", "candle", "necklace",
    "earring", "earrings", "gift", "unique", "beautiful", "elegant",
    "collection", "design", "color", "colours", "colors", "charm", "charms",
    "set", "pair", "perfect", "present", "inspired", "modern", "classic",
    "minimalist", "delicate", "luxury", "premium", "everyday", "wear",
}


def _contains_english(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", low) for word in _ENGLISH_WORDS)


_CZECH_CHARS = "ěščřžýáíéúůďťňĚŠČŘŽÝÁÍÉÚŮĎŤŇ"


def _contains_czech_diacritics(text: str) -> bool:
    if not text:
        return False
    return any(ch in _CZECH_CHARS for ch in text)


def _fill_template(tpl: str, tags: list[str]) -> str:
    if not tpl:
        return tpl
    replacements = {
        "hlavni_atribut": (tags[0] if tags else "viditelný detail"),
        "barva": (tags[1] if len(tags) > 1 else "barevný prvek"),
        "motiv": (tags[2] if len(tags) > 2 else "motiv z fotografie"),
        "atmosfera": (tags[0] if tags else "vizuální dojem"),
        "klíčový_detail": (tags[0] if tags else "detail z fotografie"),
    }
    out = tpl
    for key, val in replacements.items():
        out = out.replace("{" + key + "}", str(val))
    out = re.sub(r"\{[^}]+\}", "detail z fotografie", out)
    return out


def _strip_markdown(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("**", "").replace("__", "").replace("`", "")
    lines = cleaned.splitlines()
    result: list[str] = []
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith("#"):
            continue
        header = re.match(r"^(✨|💎)\s*(popis produktu|styl)\s*[:\-–—]*\s*$", raw, flags=re.I)
        if header:
            label = header.group(2).lower()
            result.append("✨ Popis produktu:" if label.startswith("popis") else "💎 Styl:")
            continue
        if raw.lstrip().startswith(("-", "•", "*")):
            bullet = re.sub(r"^[\-\–\•\*\s]+", "", raw).strip()
            if bullet:
                result.append(f"- {bullet}")
            continue
        raw = re.sub(r"^[\-\–\•\*\s]+", "", raw).strip()
        raw = re.sub(r"^(název|nazev|popis|description|handcrafted|styl)\s*[:\-–—]+\s*", "", raw, flags=re.I)
        if not raw:
            continue
        result.append(raw)
    return "\n".join(result)


def _normalize_multiline(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join([line for line in lines if line]).strip()


def _strip_title_from_description(title: str, description: str) -> str:
    if not title or not description:
        return description
    title_clean = _strip_emoji(title).strip()
    if not title_clean:
        return description
    desc = description.strip()
    pattern = rf"^{re.escape(title_clean)}[\s\-–—:\.]*"
    desc = re.sub(pattern, "", desc, flags=re.I).strip()
    return desc


def _sanitize_draft(title: str, description: str, tags: list[str], product_type: str) -> tuple[str, str]:
    title = title.strip()
    description = remove_banned_word_variants(description.strip())

    description = _strip_markdown(description)
    description = _strip_title_from_description(title, description)
    description = _normalize_multiline(description)

    czech_ok = _contains_czech_diacritics(title) or _contains_czech_diacritics(description)
    invalid_language = _contains_english(title) or _contains_english(description) or not czech_ok
    invalid_structure = not _has_required_structure(description)
    banned = _contains_banned_phrases(title) or _contains_banned_phrases(description)

    if invalid_language or invalid_structure or banned or not title or not description:
        title, description = build_required_structure_from_vision(product_type, tags)
        description = remove_banned_word_variants(description)

    return title, description


def build_draft_from_image(image_path: str) -> dict[str, Any]:
    vision_result = analyze_image_with_vision(image_path)
    raw_tags = normalize_tags(vision_result)
    tags_cz_full = translate_tags_to_czech(raw_tags)
    product_type = detect_product_type(tags_cz_full)
    combined_tags = list(dict.fromkeys(tags_cz_full))

    ai_template_text = load_ai_template_from_db(
        product_type=product_type,
        combined_tags=combined_tags,
    )
    title, description, rag_meta = _get_title_and_description(
        product_type,
        combined_tags,
        raw_tags=raw_tags,
        vision_tags_cz=tags_cz_full,
        ai_template_text=ai_template_text,
    )
    title, description = _sanitize_draft(title or "", description or "", combined_tags, product_type)
    rotation_index = get_emoji_rotation_index()
    description = _inject_emojis_into_description(description, tags_cz_full, rotation_index=rotation_index)
    if product_type == "bracelet":
        rag_text = get_best_rag_template(tags_cz_full, product_type)
        rag_pairs = get_rag_title_pairs(tags_cz_full, product_type, n_results=8)
        try:
            from app.modules.ai.pipeline.openai_vision import _generate_bracelet_title_with_openai
            vision_summary = (description or "").strip()[:400] or " ".join((tags_cz_full or [])[:12])
            openai_title = _generate_bracelet_title_with_openai(
                vision_summary=vision_summary,
                tags=tags_cz_full or [],
                rag_pairs=rag_pairs,
                model="gpt-4o-mini",
            )
            if openai_title:
                title = openai_title
            else:
                title = format_bracelet_name_from_image(
                    tags_cz_full,
                    description,
                    rag_text=rag_text,
                    rag_pairs=rag_pairs,
                    rotation_index=rotation_index,
                )
        except Exception:
            title = format_bracelet_name_from_image(
                tags_cz_full,
                description,
                rag_text=rag_text,
                rag_pairs=rag_pairs,
                rotation_index=rotation_index,
            )
    if title and not _contains_emoji(title):
        title = f"{random_emoji()} {title}"

    suggested_price = suggest_price(product_type=product_type, combined_tags=combined_tags)
    seo_fields = _build_seo_fields(title, description, combined_tags)

    return {
        "title": title,
        "description": description,
        "product_type": product_type,
        "combined_tags": combined_tags,
        "suggested_price_czk": suggested_price,
        **rag_meta,
        **seo_fields,
    }
