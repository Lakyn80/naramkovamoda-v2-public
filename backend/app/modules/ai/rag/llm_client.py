# -*- coding: utf-8 -*-
"""
LLM klient pro generování popisů produktů v češtině.

Vision určuje FAKTA (co je na obrázku).
RAG určuje STYL A STRUKTURU (jak formátovat text).
LLM kombinuje obojí – kopíruje strukturu z RAG, používá obsah z Vision.
"""

import os
import re
from typing import List, Optional, Tuple

from app.core.ai_config import get_openai_api_key

SYSTEM_PROMPT = """Jsi odborník na psaní e-shopových popisů produktů v češtině.
Tvým úkolem je vytvořit název a popis produktu podle těchto pravidel:

1. POUŽIJ POUZE ČESKÉ TEXTY – žádná angličtina ani cizí slova.
2. Obsah (materiály, barvy, motivy, tvary, objekty) VŽDY ber z dat z Vision – to jsou fakta o konkrétním produktu.
3. RAG / vzor slouží POUZE jako POVINNÁ ŠABLONA STRUKTURY, nikdy jako zdroj faktů.
4. ZAKÁZANÉ: „Viditelné prvky“, „Materiál“, „Typ“, „Barevné tóny“ jako nadpisy; prázdné marketingové fráze.
5. Název MUSÍ obsahovat emoji, které se HODÍ k motivu na obrázku (motýl→🦋, svíčka→🕯️, srdce→💖, tlapka→🐾, květ→🌸, skřítek→🧙‍♂️ …). Emoji se musí MĚNIT podle produktu, ne stále stejné.
6. Název musí obsahovat hlavní artikl (např. skřítek, náramek, dekorace).
7. Když je zadána POVINNÁ ŠABLONA (✨ Popis produktu, 💎 Styl), výstup MUSÍ mít přesně tuto strukturu:

<NÁZEV S EMOJI VHODNÝM K MOTIVU – např. „🦋 Zeleno-modří motýli – dekorace“>

✨ Popis produktu:
- odrážka 1 (konkrétní fakt z Vision)
- odrážka 2
- odrážka 3 (3–5 odrážek)

💎 Styl: přívlastk1, přívlastk2, přívlastk3 (2–3 přívlastky)

Vždy piš pouze v češtině. Nikdy ne výčet tagů jako odstavec."""

BANNED_PHRASES = [
    "stylový produkt s výraznými prvky ruční tvorby",
    "vhodný pro osobní použití i jako dárek",
    "vhodné jako dárek",
    "vhodný jako dárek",
    "designový produkt ruční tvorby",
    "univerzální dekorace",
    "moderní a elegantní produkt",
    "produkt vysoké kvality",
    "vysoce kvalitní",
    "precizně zpracované",
    "ručně vyráběné",
    "ruční tvorba",
    "ruční práce",
    "ruční zpracování",
    "stylový produkt",
    "designový produkt",
    "moderní produkt",
    "elegantní produkt",
    "vhodný jako dárek",
    "ideální dárek",
]

BANNED_KEYWORDS = {
    "stylový",
    "designový",
    "moderní",
    "elegantní",
    "univerzální",
    "kvalitní",
    "kvality",
    "prémiový",
    "luxusní",
    "precizní",
    "ručně",
    "handmade",
    "dárek",
}

EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")
EMOJI_FALLBACK = ["✨", "💎", "🌿", "🍀", "🧙‍♂️", "🍂", "🕯️", "🐾", "🌸", "🤍"]

ARTICLE_KEYWORDS = [
    ("skřítek", "skřítek"),
    ("gnome", "skřítek"),
    ("aranžmá", "aranžmá"),
    ("věnec", "věnec"),
    ("brož", "brož"),
    ("přívěsek do auta", "přívěsek do auta"),
    ("náramek", "náramek"),
    ("náhrdelník", "náhrdelník"),
    ("přívěsek", "přívěsek"),
    ("náušnice", "náušnice"),
    ("svíčka", "svíčka"),
    ("dekorace", "dekorace"),
    ("klíčenka", "klíčenka"),
    ("samolepka", "samolepka"),
    ("dárková kartička", "dárková kartička"),
    ("dárkový poukaz", "dárkový poukaz"),
]

DEFAULT_ARTICLE_BY_TYPE = {
    "bracelet": "náramek",
    "candle": "svíčka",
    "necklace": "náhrdelník",
    "earrings": "náušnice",
    "decor": "dekorace",
    "keychain": "klíčenka",
    "sticker": "samolepka",
    "gift card": "dárková kartička",
    "gift voucher": "dárkový poukaz",
    "other": "produkt",
}


def _pick_main_article(tags: List[str], product_type: str) -> str:
    tags_low = [t.lower().strip() for t in (tags or []) if t]
    for keyword, article in ARTICLE_KEYWORDS:
        for tag in tags_low:
            if keyword in tag:
                return article
    return DEFAULT_ARTICLE_BY_TYPE.get(product_type, "produkt")


def _contains_emoji(text: str) -> bool:
    return bool(EMOJI_RE.search(text or ""))


def _clean_title(title: str) -> str:
    if not title:
        return ""
    title = title.strip()
    title = re.sub(r"^(název|nazev|title)\s*[:\-–—]+\s*", "", title, flags=re.I).strip()
    return title


def _select_title_tags(tags: List[str]) -> List[str]:
    if not tags:
        return []
    blacklist = {
        "ruční tvorba",
        "ruční zpracování",
        "jemný design",
        "příjemná barva",
        "ruční práce",
        "klidná atmosféra",
        "precizní detail",
        "stylový produkt",
        "designový produkt",
        "moderní produkt",
        "elegantní produkt",
        "univerzální",
        "moderní",
        "elegantní",
        "kvalitní",
    }
    result: List[str] = []
    for tag in tags:
        if not tag or tag in blacklist:
            continue
        result.append(tag)
        if len(result) >= 2:
            break
    return result


def _build_vision_title(main_article: str, tags: List[str]) -> str:
    key_tags = _select_title_tags(tags)
    # Nikdy „Náramek – náramek“: za pomlčkou nesmí být jen hlavní artikl
    main_low = main_article.lower()
    key_tags = [t for t in key_tags if (t or "").strip().lower() != main_low]
    if key_tags:
        return f"{main_article.capitalize()} – {', '.join(key_tags)}"
    return main_article.capitalize()


def _strip_fixed_sections(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"✨\s*popis produktu\s*[:\-–—]*", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"💎\s*styl\s*[:\-–—]*", " ", cleaned, flags=re.I)
    return cleaned


def _clean_llm_tags(tags: List[str]) -> List[str]:
    cleaned: List[str] = []
    for tag in tags or []:
        raw = (tag or "").strip()
        if not raw:
            continue
        if re.search(r"\(en\)\s*$", raw, flags=re.I):
            continue
        raw = re.sub(r"\s*\(en\)\s*$", "", raw, flags=re.I).strip()
        if raw:
            cleaned.append(raw)
    return cleaned


def _contains_raw_english(text: str, raw_tags: List[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    if "(en)" in low:
        return True
    for tag in raw_tags or []:
        t = (tag or "").strip().lower()
        if not t or len(t) < 3:
            continue
        if re.search(rf"\b{re.escape(t)}\b", low):
            return True
    return False


def _normalize_for_phrase_match(text: str) -> str:
    if not text:
        return ""
    cleaned = text.lower()
    cleaned = re.sub(r"[^a-z0-9ěščřžýáíéúůďťň ]+", " ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned


def _contains_banned_phrases(text: str) -> bool:
    if not text:
        return False
    normalized = _normalize_for_phrase_match(text)
    if not normalized:
        return False
    for phrase in BANNED_PHRASES:
        if _normalize_for_phrase_match(phrase) in normalized:
            return True
    for keyword in BANNED_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", normalized):
            return True
    return False


def _tokenize(text: str) -> List[str]:
    cleaned = _strip_fixed_sections(text.lower())
    cleaned = re.sub(r"[^a-z0-9ěščřžýáíéúůďťň ]+", " ", cleaned)
    return [w for w in cleaned.split() if w]


def _bigram_set(words: List[str]) -> set[str]:
    if len(words) < 2:
        return set()
    return {" ".join(words[i : i + 2]) for i in range(len(words) - 1)}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _is_original_enough(description: str, rag_template: str) -> bool:
    desc_words = _tokenize(description)
    tmpl_words = _tokenize(rag_template)
    desc_bi = _bigram_set(desc_words)
    tmpl_bi = _bigram_set(tmpl_words)
    similarity = _jaccard_similarity(desc_bi, tmpl_bi)
    return similarity <= 0.5


def _has_required_structure(description: str, allow_mandatory_format: bool = False) -> bool:
    if not description:
        return False
    text = " ".join(description.split())
    if len(text) < 50:
        return False
    if re.search(r"\b(viditelné prvky|barevné tóny|materiál|typ)\b", text, flags=re.I):
        return False
    if "✨" in description and "💎" in description and "Popis produktu" in description and "Styl" in description:
        return True
    if "✨" in text or "💎" in text:
        return False
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    return len(sentences) >= 2


def _title_has_article(title: str, main_article: str) -> bool:
    if not title or not main_article:
        return False
    return main_article.lower() in title.lower()


def _title_is_article_repeat(title: str, main_article: str) -> bool:
    """Zakázaný tvar typu „Náramek – náramek“ (stejné slovo před i za pomlčkou)."""
    if not title or not main_article:
        return False
    for sep in (" – ", " - ", " –", " -"):
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts) == 2:
                a = re.sub(EMOJI_RE, "", parts[0]).strip().lower()
                b = parts[1].strip().lower()
                if a == b or a == main_article.lower() and b == main_article.lower():
                    return True
    return False


def _ensure_title_requirements(title: str, main_article: str) -> str:
    title = _clean_title(title)
    if main_article and not _title_has_article(title, main_article):
        title = f"{main_article.capitalize()} {title}".strip()
    if title and not _contains_emoji(title):
        title = f"{title} {EMOJI_FALLBACK[0]}"
    return title.strip()


def _get_llm_client():
    """Vrátí OpenAI klienta pro generování názvu a popisu (bez DeepSeek)."""
    api_key = get_openai_api_key()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAI(api_key=api_key), model
    except ImportError:
        return None


def generate_product_description(
    vision_tags_cz: List[str],
    product_type: str,
    rag_template: str,
    prefer_vision_title: bool = False,
    vision_raw_tags: Optional[List[str]] = None,
    use_mandatory_structure: bool = False,
) -> Optional[Tuple[str, str]]:
    """
    Vygeneruje název a popis produktu v češtině.

    - vision_tags_cz: fakta z Vision (materiály, barvy, motivy) v češtině
    - vision_raw_tags: surové Vision tagy (většinou anglicky) – použij jako doplněk a přelož do češtiny
    - product_type: bracelet, candle, necklace, earrings, decor, other
    - rag_template: vzorový text z RAG (struktura a styl); při use_mandatory_structure je to povinná šablona
    - use_mandatory_structure: když RAG nemá shodu, výstup MUSÍ mít strukturu ✨ Popis produktu / 💎 Styl

    Vrací (title, description) nebo None při chybě / chybějícím API klíči.
    """
    client_result = _get_llm_client()
    if not client_result:
        return None

    client, model = client_result
    clean_tags = _clean_llm_tags(vision_tags_cz)
    tags_text = ", ".join(clean_tags) if clean_tags else "obecný produkt"
    raw_tags = [t for t in (vision_raw_tags or []) if t]
    raw_tags_text = ", ".join(raw_tags) if raw_tags else ""
    main_article = _pick_main_article(vision_tags_cz, product_type)

    if use_mandatory_structure:
        extra_rule = (
            "VÝSTUP MUSÍ MÍT PŘESNĚ TUTO STRUKTURU: název s emoji vhodným k motivu, "
            "pak „✨ Popis produktu:“ s 3–5 odrážkami z Vision, pak „💎 Styl:“ a 2–3 přívlastky."
        )
        template_label = "POVINNÁ ŠABLONA STRUKTURY"
    else:
        extra_rule = (
            "VZOR JE REÁLNÝ POPIS Z E-SHOPU. KOPÍRUJ PŘESNĚ JEHO STYL – bohatý, vyprávěcí, s osobností. "
            "Název má být výstižný a atraktivní (např. „Růžová radost“, „Jemný třpyt“), NE generický („Šperk – náramek“). "
            "Popis má být jako ve vzoru: odstavce, osobní tón, případně sekce „Proč si ho zamiluješ“ s odrážkami. "
            "NIKDY ne výčet tagů jako „šperk, náramek, růžová“ – piš plné věty a přirozený text."
        )
        template_label = "VZOR Z RAG (reálný produkt – kopíruj tento styl a formát)"

    user_content = f"""FAKTA Z VISION (co je na obrázku – POUŽIJ TYTO ÚDAJE):
{tags_text}

SUROVÉ VISION TAGY (PŘELOŽ DO ČEŠTINY, POKUD JSOU RELEVANTNÍ):
{raw_tags_text or "není k dispozici"}

HLAVNÍ ARTIKL (musí být v názvu nebo popisu):
{main_article}

{template_label}:
---
{rag_template}
---

Vytvoř název a popis v češtině. Název na první řádek (s emoji vhodným k motivu), prázdný řádek, pak popis.
ŽÁDNÁ ANGLICKÁ SLOVA. Žádné „Viditelné prvky“, „Materiál“, „Typ“.
{extra_rule}
Pouze český text."""

    try:
        last_title = ""
        last_description = ""
        for attempt in range(1, 4):
            prompt = user_content
            if attempt > 1:
                prompt = f"""{user_content}

POZOR: Předchozí výstup nesplnil pravidla. Vygeneruj NOVOU verzi.
Název musí obsahovat hlavní artikl „{main_article}“ a emoji a NESMÍ obsahovat zakázané fráze.
Popis musí být přirozený a konkrétní v 2–4 větách, žádné seznamy tagů, žádné sekce.
Nesmíš použít žádné anglické slovo; pokud něco neznáš, popiš to česky obecně.
Používej pouze konkrétní fakta z Vision. Žádné obecné marketingové fráze.
"""
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=800,
            )
            text = (resp.choices[0].message.content or "").strip()
            if not text:
                continue

            parts = text.split("\n\n", 1)
            title = parts[0].strip() if parts else ""
            description = parts[1].strip() if len(parts) > 1 else text
            title = _clean_title(title)
            last_title = title
            last_description = description

            if use_mandatory_structure:
                if not _title_has_article(title, main_article):
                    continue
            else:
                title_has_ref = _title_has_article(title, main_article) or any(
                    (t or "").lower() in (title or "").lower()
                    for t in (vision_tags_cz or [])[:8] if t and len(str(t).strip()) > 2
                )
                if not title_has_ref:
                    continue
            if not _contains_emoji(title):
                continue
            if _title_is_article_repeat(title, main_article):
                continue
            if not _has_required_structure(description):
                continue
            if _contains_raw_english(title, raw_tags) or _contains_raw_english(description, raw_tags):
                continue
            if _contains_banned_phrases(title) or _contains_banned_phrases(description):
                continue
            if not use_mandatory_structure and not _is_original_enough(description, rag_template):
                continue

            return title, description

        if last_title or last_description:
            if not _contains_banned_phrases(last_title) and not _contains_banned_phrases(last_description):
                if _has_required_structure(last_description or ""):
                    if prefer_vision_title or _title_is_article_repeat(last_title, main_article):
                        last_title = _build_vision_title(main_article, vision_tags_cz)
                    last_title = _ensure_title_requirements(last_title, main_article)
                    return last_title, last_description
        return None
    except Exception:
        return None
