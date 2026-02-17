# -*- coding: utf-8 -*-
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

from .media_repository import get_media_assets_by_session
from .vision_client import analyze_image_with_vision, normalize_tags
from .templates import get_fallback_template

logger = logging.getLogger(__name__)

EMOJI_POOL = [
    "💚","🌿","🍀","✨","💎","🕯️","🐾","🦋","🌸","💖",
    "⭐","🌙","🌊","🔥","🧿","🎁","🧵","🧩","🌈","🤍"
]

def random_emoji() -> str:
    import random
    return random.choice(EMOJI_POOL)

def _contains_emoji(text: str) -> bool:
    return bool(re.search(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", text or ""))

TAG_CZ = {
    "natural material": "přírodní materiál",
    "metal": "kov",
    "silver": "stříbrná",
    "gold": "zlatá",
    "gemstone": "drahokam",
    "crystal": "křišťál",
    "glass": "sklo",
    "wood": "dřevo",
    "wax": "vosk",

    "butterfly": "motýl",
    "butterflies": "motýli",

    "bead": "korálek",
    "beads": "korálky",
    "beaded": "korálkový",

    "bracelet": "náramek",
    "wristband": "náramek",
    "anklet": "náramek na nohu",
    "necklace": "náhrdelník",
    "pendant": "přívěsek",
    "charm": "přívěsek",
    "keychain": "klíčenka",
    "key ring": "klíčenka",
    "lanyard": "šňůrka na telefon",
    "phone strap": "šňůrka na telefon",
    "car pendant": "přívěsek do auta",
    "car charm": "přívěsek do auta",
    "earring": "náušnice",
    "earrings": "náušnice",
    "jewelry": "šperk",
    "jewellery": "šperk",
    "jewelry set": "šperkový set",

    "candle": "svíčka",
    "candles": "svíčky",
    "decor": "dekorace",
    "decoration": "dekorace",
    "ornament": "dekorace",
    "gnome": "skřítek",

    "sticker": "samolepka",
    "stickers": "samolepky",
    "decal": "samolepka",
    "decals": "samolepky",
    "adhesive": "samolepka",
    "sheet": "arch",
    "set": "sada",
    "pack": "sada",
    "gift card": "dárková kartička",
    "greeting card": "dárková kartička",
    "voucher": "dárkový poukaz",
    "gift voucher": "dárkový poukaz",

    "pacifier clip": "provázek na dudlík",
    "teether clip": "provázek na kousátko",
    "diy kit": "kreativní sada",
    "craft kit": "kreativní sada",

    
    
    

    "blue": "modrá",
    "green": "zelená",
    "black": "černá",
    "white": "bílá",
    "red": "červená",
    "yellow": "žlutá",
    "brown": "hnědá",
    "pink": "růžová",
    "purple": "fialová",
    "orange": "oranžová",
    "gray": "šedá",

    "flower": "květ",
    "flowers": "květy",
    "floral": "květinový",
    "leaf": "list",
    "leaves": "listy",
    "heart": "srdce",
    "hearts": "srdce",
    "star": "hvězda",
    "stars": "hvězdy",
    "moon": "měsíc",
    "sun": "slunce",
    "hologram": "hologram",
    "glitter": "třpyt",
    "sparkle": "třpyt",
    "pearl": "perla",
    "pearls": "perly",
    "stone": "kámen",
    "stones": "kameny",
    "ribbon": "stuha",
    "string": "šňůrka",
    "thread": "nit",
    "wooden": "dřevěný",
    "bone": "kost",
    "dog collar": "obojek pro psa",
    "collar": "obojek",
    "paw": "tlapka",
    "love": "láska",
    "jewelry making": "výroba šperků",
    "plastic": "plast",
}

_CZECH_CHARS = "ěščřžýáíéúůďťňĚŠČŘŽÝÁÍÉÚŮĎŤŇ"


def _looks_czech(tag: str) -> bool:
    if not tag:
        return False
    if any(ch in _CZECH_CHARS for ch in tag):
        return True
    if tag.lower().startswith("rozměr "):
        return True
    return False


def _fallback_translate(tag: str) -> str:
    clean = (tag or "").strip()
    if not clean:
        return clean
    if _looks_czech(clean):
        return clean
    if clean.lower().endswith("(en)"):
        return clean
    return f"{clean} (EN)"


def translate_tags_to_czech(tags: List[str]) -> List[str]:
    """
    Vrátí seznam českých tagů ve stejném pořadí a počtu jako vstup.
    Neznámé tagy NEZAHOZUJE, ale označí fallbackem.
    """
    translated: List[str] = []
    for t in tags or []:
        t_low = (t or "").lower().strip()
        if t_low in TAG_CZ:
            translated.append(TAG_CZ[t_low])
        else:
            translated.append(_fallback_translate(t))
    return translated

VISION_TO_PRODUCT_TYPE = {
    "náramek": "bracelet",
    "náramky": "bracelet",
    "náramek na nohu": "bracelet",
    "šperk": "bracelet",
    "šperk na tělo": "bracelet",
    "svíčka": "candle",
    "svíčky": "candle",
    "náhrdelník": "necklace",
    "náhrdelníky": "necklace",
    "přívěsek": "necklace",
    "náušnice": "earrings",
    "dekorace": "decor",
    "klíčenka": "keychain",
    "samolepka": "sticker",
    "dárková kartička": "gift card",
    "dárkový poukaz": "gift voucher",
}

def detect_product_type(tags: List[str]) -> str:
    if not tags:
        return "other"
    normalized = [t.lower() for t in tags]
    for tag in normalized:
        if tag in VISION_TO_PRODUCT_TYPE:
            return VISION_TO_PRODUCT_TYPE[tag]
    return "other"


_GENERIC_TAGS = set()

_COLOR_TAGS = {
    "modrá",
    "zelená",
    "černá",
    "bílá",
    "červená",
    "žlutá",
    "hnědá",
    "růžová",
    "fialová",
    "oranžová",
    "šedá",
    "stříbrná",
    "zlatá",
}

_MATERIAL_TAGS = {
    "přírodní materiál",
    "kov",
    "stříbrná",
    "zlatá",
    "drahokam",
    "křišťál",
    "sklo",
    "dřevo",
    "dřevěný",
    "vosk",
    "kámen",
    "kameny",
    "perla",
    "perly",
}

_STYLE_ADJ_BY_TAG = {
    "kov": "kovový",
    "stříbrná": "stříbrný",
    "zlatá": "zlatý",
    "sklo": "skleněný",
    "dřevo": "dřevěný",
    "dřevěný": "dřevěný",
    "vosk": "voskový",
    "křišťál": "křišťálový",
    "drahokam": "drahokamový",
    "perla": "perlový",
    "perly": "perlový",
    "kámen": "kamenný",
    "kameny": "kamenný",
    "korálky": "korálkový",
    "korálek": "korálkový",
    "motýl": "motýlí",
    "motýli": "motýlí",
    "květ": "květinový",
    "květy": "květinový",
    "list": "listový",
    "listy": "listový",
    "srdce": "srdcový",
    "hvězda": "hvězdný",
    "hvězdy": "hvězdný",
}

_ARTICLE_BY_TYPE = {
    "bracelet": "náramek",
    "candle": "svíčka",
    "necklace": "náhrdelník",
    "earrings": "náušnice",
    "decor": "dekorace",
    "keychain": "klíčenka",
    "sticker": "samolepka",
    "gift card": "dárková kartička",
    "gift voucher": "dárkový poukaz",
    "other": "dekorace",
}

# Povinná šablona struktury, když RAG nemá shodu – LLM i fallback ji musí dodržet
MANDATORY_STRUCTURE_TEMPLATE = """🦋 Zeleno-modří motýli – dekorace

✨ Popis produktu:
- Jemné papírové motýlky v modrých a zelených tónech
- Detailní kresba žilek na křídlech
- Lehké, tenké provedení vhodné k nalepení

💎 Styl: přírodní, svěží, hravý"""

# 8 fixních originál vzorů (varianta B) – při chybějící RAG shodě se vybere nejbližší podle embeddingu
ORIGINAL_FALLBACK_TEMPLATES: List[tuple[str, str, str]] = [
    (
        "Podzimní skřítek v aranžmá 🍂🧙‍♂️",
        "Tento roztomilý skřítek zasazený do podzimního květinového aranžmá vnese do vašeho domova teplo, hravost a kousek přírody. Je ideální jako dekorace na stůl, komodu či dárek pro milovníky přírodních motivů.\n\n"
        "✨ Popis produktu:\n"
        "- Dekorativní skřítek obklopený umělými květy a listy\n"
        "- Stabilní základ na kulatém podkladu\n"
        "- Kombinace podzimních barev a přírodních detailů\n\n"
        "💎 Styl: útulný, hravý, přírodní",
        "decor",
    ),
    (
        "Květinový skřítek s růžemi 🌹🧙‍♀️",
        "Romantický skřítek obklopený sytě červenými růžemi a jemnými bílými kvítky vytváří elegantní a zároveň hravý dekorační prvek. Skvěle se hodí jako dárek nebo stylová dekorace do interiéru.\n\n"
        "✨ Popis produktu:\n"
        "- Dekorativní skřítek v květinovém věnci\n"
        "- Výrazné červené růže a jemné doplňky\n"
        "- Pečlivé ruční naaranžování\n\n"
        "💎 Styl: romantický, jemný, dekorativní",
        "decor",
    ),
    (
        "Modro-fialové motýlkové samolepky 🦋💙",
        "Sada elegantních motýlků v odstínech modré a fialové, které dodají vašim projektům kouzelný a kreativní vzhled. Ideální na zdobení deníků, dárků, telefonů či dekorací.\n\n"
        "✨ Popis produktu:\n"
        "- Realistický design motýlů\n"
        "- Kombinace modrých a fialových tónů\n"
        "- Vhodné pro kreativní dekorace\n\n"
        "💎 Styl: snový, umělecký, jemný",
        "sticker",
    ),
    (
        "Zeleno-modří motýli – dekorace 🦋💚",
        "Krásná sada barevných motýlků v přírodních odstínech zelené a modré. Skvělé pro scrapbooking, dárkové balení nebo výzdobu pokoje.\n\n"
        "✨ Popis produktu:\n"
        "- Lehký a detailní design\n"
        "- Přírodní barevná kombinace\n"
        "- Vhodné pro DIY projekty\n\n"
        "💎 Styl: přírodní, kreativní, svěží",
        "decor",
    ),
    (
        "Klíčenka „Men Day“ 🌈🔑",
        "Stylová klíčenka s barevnými korálky a metalickým holografickým přívěskem. Moderní a výrazný doplněk pro každodenní použití.\n\n"
        "✨ Popis produktu:\n"
        "- Barevné korálky navlečené na pevném lanku\n"
        "- Holografický přívěsek s nápisem\n"
        "- Kovový kroužek na klíče\n\n"
        "💎 Styl: moderní, hravý, výrazný",
        "keychain",
    ),
    (
        "Pero „Pro štěstí 😊“ ✒️🍀",
        "Elegantní pero s jemným nápisem „Pro štěstí :-)\", které je skvělým malým dárkem pro blízké. Hodí se do práce, školy nebo jako milé gesto.\n\n"
        "✨ Popis produktu:\n"
        "- Stylové kovové tělo pera\n"
        "- Gradientní barevný přechod\n"
        "- Vhodné jako drobný dárek\n\n"
        "💎 Styl: jemný, osobní, inspirativní",
        "other",
    ),
    (
        "Zeleno-černý korálkový náramek 🟢⚫",
        "Jednoduchý elastický náramek z lesklých skleněných korálků v kombinaci zelené, černé a šedé vytváří čistý a harmonický vzhled. Hodí se jako každodenní doplněk i jemný akcent k minimalistickému stylu.\n\n"
        "✨ Popis produktu:\n"
        "- Kulaté skleněné korálky se světelným efektem\n"
        "- Pravidelné střídání zelených, černých a šedých tónů\n"
        "- Pružná gumička pro snadné navlékání\n\n"
        "💎 Styl: moderní, svěží, minimalistický",
        "bracelet",
    ),
    (
        "Křišťálový náramek s psím přívěškem 🐾✨",
        "Jemný průhledný náramek z popraskaných křišťálových korálků doplněný kovovým přívěškem psa. Působí lehce, elegantně a zároveň osobně – jako symbol lásky ke zvířatům.\n\n"
        "✨ Popis produktu:\n"
        "- Průsvitné křišťálové korálky s vnitřní strukturou\n"
        "- Stříbrný kovový přívěšek ve tvaru psa\n"
        "- Pevné zapínání s prodlužovacím řetízkem\n\n"
        "💎 Styl: jemný, čistý, osobní",
        "bracelet",
    ),
]

# Emoji podle motivu – název musí obsahovat emoji vhodné k produktu (měnit podle obrázku)
EMOJI_BY_MOTIF = [
    ("motýl", "🦋"), ("motýli", "🦋"), ("butterfly", "🦋"),
    ("květ", "🌸"), ("květy", "🌸"), ("květina", "🌸"), ("květiny", "🌸"),
    ("flower", "🌸"), ("flowers", "🌸"), ("růže", "🌷"), ("tulipán", "🌷"),
    ("sedmikráska", "🌼"), ("pampeliška", "🌼"),
    ("list", "🍃"), ("listy", "🍃"), ("příroda", "🌿"), ("přírodní", "🌿"),
    ("leaf", "🍃"), ("leaves", "🍃"), ("bylina", "🌿"), ("bylinky", "🌿"),
    ("srdce", "💖"), ("hearts", "💖"), ("láska", "💖"), ("love", "❤️"),
    ("kočka", "🐱"), ("kočky", "🐱"), ("cat", "🐱"),
    ("tlapka", "🐾"), ("paw", "🐾"), ("paws", "🐾"),
    ("náramek", "💎"), ("šperk", "💎"), ("náhrdelník", "📿"), ("jewelry", "💎"),
    ("svíčka", "🕯️"), ("svíčky", "🕯️"), ("candle", "🕯️"),
    ("přívěsek", "🔗"), ("pendant", "🔗"), ("charm", "🔗"),
    ("hvězda", "⭐"), ("hvězdy", "⭐"), ("star", "⭐"), ("stars", "⭐"),
    ("hvězdice", "🌟"), ("mořská hvězdice", "🌟"), ("starfish", "🌟"),
    ("třpyt", "✨"), ("sparkle", "✨"),
    ("anděl", "👼"), ("andělé", "👼"), ("angel", "👼"),
    ("perla", "🤍"), ("perly", "🤍"), ("pearl", "🤍"), ("pearls", "🤍"),
    ("strom", "🌳"), ("stromy", "🌳"), ("tree", "🌳"), ("dřevo", "🌳"),
    ("moře", "🌊"), ("oceán", "🌊"), ("sea", "🌊"), ("ocean", "🌊"),
    ("slunce", "☀️"), ("sun", "☀️"),
    ("měsíc", "🌙"), ("moon", "🌙"),
    ("kůň", "🐴"), ("horse", "🐴"), ("hřebec", "🐴"),
    ("skřítek", "🧙‍♂️"), ("skřítci", "🧙‍♂️"), ("gnome", "🧙‍♂️"),
    ("lesní skřítek", "🧚"), ("lesní", "🍄"), ("houba", "🍄"), ("mushroom", "🍄"),
    ("elf", "🧝‍♂️"), ("elfové", "🧝‍♂️"),
    ("víla", "🧚"), ("víly", "🧚"), ("fairy", "🧚"),
]
EMOJI_DEFAULT_POOL = [
    "🦋", "🌸", "🍃", "💖", "🐱", "🐾", "💎", "🌙", "⭐", "🌊",
    "🌿", "🌼", "🕯️", "🔗", "🧙‍♂️", "🧚", "🤍", "☀️", "📿", "✨",
]

_HEART_EMOJI_POOL = ["💖", "💗", "💕", "💞", "❤️", "🩷"]
_HEART_EMOJI_SET = set(_HEART_EMOJI_POOL)
_HEART_EMOJI_PATTERN = r"(?:💖|💗|💕|💞|❤️‍🔥|❤️|🩷)"

_BRACELET_GENERIC_TAGS = {
    "náramek",
    "náramky",
    "šperk",
    "šperk na tělo",
    "tělový šperk",
    "přívěsek",
    "přívěšek",
    "bracelet",
    "bracelets",
    "bransoletka",
    "bransoletki",
    "armband",
    "armbånd",
    "pulsera",
    "pulseras",
    "bracciale",
    "jewelry",
    "doplněk",
    "doplnky",
    "barva",
    "barvy",
}

_BRACELET_PRIMARY_MOTIF_TAGS = {
    "tlapka",
    "srdce",
    "motýl",
    "motýli",
    "květ",
    "květy",
    "hvězda",
    "hvězdy",
    "list",
    "listy",
}

_BRACELET_FALLBACK_MOTIF_TAGS = {
    "perla",
    "perly",
    "korálek",
    "korálky",
    "řetízek",
    "křišťál",
    "drahokam",
}

_BRACELET_DISALLOWED_SECOND_TAGS = {
    "kámen",
    "kameny",
    "doplněk",
    "doplnky",
    "barva",
    "barvy",
}

_BRACELET_BANNED_EMOJIS = {
    "💎",
    "📿",
    "🔗",
}

_BRACELET_FALLBACK_EMOJIS = ["📿", "🔗"]

_BRACELET_BANNED_WORD_PREFIXES = (
    "přívěs",
    "náram",
    "bracelet",
    "bransolet",
    "armband",
    "armb",
    "pulser",
    "braccial",
    "dopln",
    "barv",
)

_BRACELET_FORBIDDEN_EMOJI_PAIR = {"📿", "🔗"}

# Slova, která NESMÍ být v názvu náramku (ani jako první, ani jako druhé slovo)
_BRACELET_FORBIDDEN_TITLE_WORDS = {
    "náramek", "náramky", "šperk", "doplněk", "doplnky",
    "jemná", "jemný", "radost", "elegantní", "stylová", "stylový",
    "korálkový", "korálková", "bracelet", "bransoletka",
}

_COLOR_TO_EMOJI = {
    "růžová": "💖",
    "červená": "❤️",
    "modrá": "💙",
    "zelená": "💚",
    "žlutá": "💛",
    "černá": "🖤",
    "bílá": "🤍",
    "stříbrná": "✨",
    "zlatá": "✨",
}

_MATERIAL_TO_EMOJI = {
    "přírodní": "🌿",
    "list": "🌿",
    "listy": "🌿",
    "perla": "🤍",
    "perly": "🤍",
    "křišťál": "✨",
    "sklo": "✨",
    "třpyt": "✨",
}


def _normalize_bracelet_name_tags(tags: List[str]) -> List[str]:
    cleaned: List[str] = []
    for tag in tags or []:
        raw = str(tag or "").strip().lower()
        if not raw:
            continue
        raw = re.sub(r"\s*\(en\)\s*$", "", raw, flags=re.I).strip()
        if not raw or "(en)" in raw:
            continue
        if raw in _BRACELET_GENERIC_TAGS:
            continue
        if any(raw.startswith(prefix) for prefix in _BRACELET_BANNED_WORD_PREFIXES):
            continue
        cleaned.append(raw)
    return _dedupe(cleaned)


def _pick_word_from_tag(tag: str, *, prefer_last: bool = False) -> str:
    if not tag:
        return ""
    parts = []
    for part in re.split(r"[\s/]+", tag):
        if not part:
            continue
        if any(part.startswith(prefix) for prefix in _BRACELET_BANNED_WORD_PREFIXES):
            continue
        parts.append(part)
    if not parts:
        return ""
    return parts[-1] if prefer_last else parts[0]


def _word_root(word: str) -> str:
    w = (word or "").lower().strip()
    if not w:
        return ""
    w = re.sub(r"(ového|ových|ové|ová|ový)$", "", w)
    w = re.sub(r"(ých|ými|ému|á|é|í|ý|y|a|e|i|o|u)$", "", w)
    return w


def _same_stem(a: str, b: str) -> bool:
    ra = _word_root(a)
    rb = _word_root(b)
    if not ra or not rb:
        return False
    if ra == rb:
        return True
    if len(ra) >= 4 and rb.startswith(ra):
        return True
    if len(rb) >= 4 and ra.startswith(rb):
        return True
    return False


def _title_word(word: str) -> str:
    if not word:
        return ""
    cleaned = re.sub(r"[^\wěščřžýáíéúůďťň]+", "", word, flags=re.I).strip()
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _extract_two_words_from_rag_title(rag_text: str) -> tuple[str, str] | None:
    if not rag_text:
        return None
    title_line = ""
    for line in rag_text.splitlines():
        if line.strip():
            title_line = line.strip()
            break
    if not title_line:
        return None
    cleaned = _strip_emoji(title_line)
    cleaned = re.sub(r"\s*[-–—]\s*\d+(?:[.,]\d+)?\s*cm\b.*$", "", cleaned, flags=re.I).strip()
    quote_match = re.search(r"„([^“]+)“", cleaned) or re.search(r"\"([^\"]+)\"", cleaned)
    if quote_match:
        cleaned = quote_match.group(1).strip()
    words: list[str] = []
    for part in re.split(r"\s+", cleaned):
        word = re.sub(r"[^\wěščřžýáíéúůďťň-]+", "", part, flags=re.I).strip("-").strip()
        if not word:
            continue
        word_low = word.lower()
        if word_low in _BRACELET_GENERIC_TAGS:
            continue
        if any(word_low.startswith(prefix) for prefix in _BRACELET_BANNED_WORD_PREFIXES):
            continue
        words.append(word_low)
    if len(words) < 2:
        return None
    if _same_stem(words[0], words[1]):
        return None
    return words[0], words[1]


def _get_existing_title_pairs() -> set[tuple[str, str]]:
    try:
        from app.db.session import SessionLocal
        from app.db.models import Product, ProductVariant
    except Exception:
        return set()
    pairs: set[tuple[str, str]] = set()
    try:
        db = SessionLocal()
        try:
            names = []
            names.extend([p[0] for p in db.query(Product.name).all()])
            names.extend([v[0] for v in db.query(ProductVariant.variant_name).all()])
        finally:
            db.close()
    except Exception:
        return set()
    for name in names:
        pair = _extract_two_words_from_rag_title(str(name))
        if pair:
            pairs.add((pair[0].lower(), pair[1].lower()))
    return pairs


def _pick_first_word(tags: List[str]) -> str:
    for tag in tags:
        if tag in _COLOR_TAGS:
            return tag
    for tag in tags:
        if tag in _STYLE_ADJ_BY_TAG:
            return _STYLE_ADJ_BY_TAG[tag]
    for tag in tags:
        word = _pick_word_from_tag(tag, prefer_last=False)
        if word:
            return word
    return ""


def _pick_second_word(tags: List[str], used: str) -> str:
    for tag in tags:
        if tag in _BRACELET_PRIMARY_MOTIF_TAGS:
            word = _pick_word_from_tag(tag, prefer_last=True)
            if word and word != used and not _same_stem(word, used):
                return word
    for tag in tags:
        if tag in _BRACELET_FALLBACK_MOTIF_TAGS:
            word = _pick_word_from_tag(tag, prefer_last=True)
            if word and word != used and not _same_stem(word, used):
                return word
    for tag in tags:
        if (
            tag in _COLOR_TAGS
            or tag in _BRACELET_GENERIC_TAGS
            or tag in _BRACELET_DISALLOWED_SECOND_TAGS
        ):
            continue
        word = _pick_word_from_tag(tag, prefer_last=True)
        if word and word != used and not _same_stem(word, used):
            return word
    for tag in tags:
        word = _pick_word_from_tag(tag, prefer_last=True)
        if word and word != used and not _same_stem(word, used):
            return word
    return ""


def _pick_heart_emojis(tags: List[str], count: int = 2) -> List[str]:
    if not _HEART_EMOJI_POOL:
        return []
    seed_text = "|".join([t.lower().strip() for t in tags or []])
    seed = sum(ord(ch) for ch in seed_text)
    first_idx = seed % len(_HEART_EMOJI_POOL)
    first = _HEART_EMOJI_POOL[first_idx]
    if count <= 1:
        return [first]
    second_idx = (first_idx + 1) % len(_HEART_EMOJI_POOL)
    second = _HEART_EMOJI_POOL[second_idx]
    if second == first and len(_HEART_EMOJI_POOL) > 1:
        second = _HEART_EMOJI_POOL[(second_idx + 1) % len(_HEART_EMOJI_POOL)]
    return [first, second]


def _rotate_emojis(emojis: List[str], rotation_index: int | None) -> List[str]:
    if not emojis:
        return emojis
    if not rotation_index:
        return emojis
    idx = rotation_index % len(emojis)
    if idx == 0:
        return emojis
    return emojis[idx:] + emojis[:idx]


def _pick_bracelet_emojis(tags: List[str], rotation_index: int | None = None) -> List[str]:
    emojis: List[str] = []
    tags_low = [t.lower().strip() for t in tags if t]
    def is_heart(emoji: str) -> bool:
        return emoji in _HEART_EMOJI_SET
    def add_emoji(emoji: str | None) -> None:
        if not emoji:
            return
        if emoji in _BRACELET_BANNED_EMOJIS:
            return
        if emoji in emojis:
            return
        if is_heart(emoji) and any(is_heart(existing) for existing in emojis):
            return
        emojis.append(emoji)

    for keyword, emoji in EMOJI_BY_MOTIF:
        if keyword in _BRACELET_GENERIC_TAGS:
            continue
        for tag in tags_low:
            if keyword in tag and emoji not in emojis:
                add_emoji(emoji)
        if len(emojis) >= 2:
            break
    if len(emojis) < 2:
        for tag in tags_low:
            add_emoji(_COLOR_TO_EMOJI.get(tag))
            if len(emojis) >= 2:
                break
    if len(emojis) < 2:
        for tag in tags_low:
            add_emoji(_MATERIAL_TO_EMOJI.get(tag))
            if len(emojis) >= 2:
                break
    if len(emojis) < 2:
        for emoji in _pick_heart_emojis(tags_low, count=2):
            add_emoji(emoji)
            if len(emojis) >= 2:
                break
    if len(emojis) < 2:
        for emoji in EMOJI_DEFAULT_POOL:
            add_emoji(emoji)
            if len(emojis) >= 2:
                break
    emojis = _rotate_emojis(emojis, rotation_index)
    return emojis[:2]


def _strip_emoji(text: str) -> str:
    if not text:
        return text
    return re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", text).strip()

def _strip_heart_emojis(text: str) -> str:
    if not text:
        return text
    return re.sub(_HEART_EMOJI_PATTERN, "", text)


def get_emoji_rotation_index() -> int:
    try:
        from app.db.session import SessionLocal
        from app.db.models import Product
    except Exception:
        return 0
    try:
        db = SessionLocal()
        try:
            count = db.query(Product.id).count()
        finally:
            db.close()
        return int(count) // 3 if count else 0
    except Exception:
        return 0

def _pick_description_emojis(tags: List[str], rotation_index: int | None = None) -> List[str]:
    emojis: List[str] = []
    tags_low = [t.lower().strip() for t in (tags or []) if t]
    def is_heart(emoji: str) -> bool:
        return emoji in _HEART_EMOJI_SET

    def add_emoji(emoji: str | None) -> None:
        if not emoji:
            return
        if emoji in _BRACELET_BANNED_EMOJIS:
            return
        if emoji in emojis:
            return
        if is_heart(emoji) and any(is_heart(existing) for existing in emojis):
            return
        emojis.append(emoji)

    for keyword, emoji in EMOJI_BY_MOTIF:
        for tag in tags_low:
            if keyword in tag:
                add_emoji(emoji)
        if len(emojis) >= 2:
            break
    if len(emojis) < 2:
        for tag in tags_low:
            add_emoji(_COLOR_TO_EMOJI.get(tag))
            if len(emojis) >= 2:
                break
    if len(emojis) < 2:
        for tag in tags_low:
            add_emoji(_MATERIAL_TO_EMOJI.get(tag))
            if len(emojis) >= 2:
                break
    if len(emojis) < 2:
        for emoji in _pick_heart_emojis(tags_low, count=2):
            add_emoji(emoji)
            if len(emojis) >= 2:
                break
    emojis = _rotate_emojis(emojis, rotation_index)
    return emojis[:2]


def _inject_emojis_into_description(
    description: str,
    vision_tags: List[str],
    rotation_index: int | None = None,
) -> str:
    if not description:
        return description
    if not vision_tags:
        return description

    description = _strip_heart_emojis(description)
    tags = _normalize_bracelet_name_tags(vision_tags)
    emoji_candidates = _pick_description_emojis(tags, rotation_index=rotation_index)
    if not emoji_candidates:
        return description

    lines = description.splitlines()
    updated: list[str] = []
    inserted = 0
    for line in lines:
        if inserted >= len(emoji_candidates):
            updated.append(line)
            continue
        raw = line.strip()
        if raw.startswith("-"):
            cleaned = _strip_emoji(raw)
            emoji = emoji_candidates[inserted]
            updated.append(re.sub(r"^-\s*", f"- {emoji} ", cleaned))
            inserted += 1
            continue
        if raw and not raw.startswith("✨") and not raw.startswith("💎") and "Styl:" not in raw:
            cleaned = _strip_emoji(raw)
            emoji = emoji_candidates[inserted]
            updated.append(f"{emoji} {cleaned}")
            inserted += 1
            continue
        updated.append(line)
    return "\n".join(updated)


def format_bracelet_name_from_image(
    vision_tags: List[str],
    description: str,
    rag_text: str | None = None,
    rag_pairs: list[tuple[str, str]] | None = None,
    rotation_index: int | None = None,
) -> str:
    """
    Vytvoří název náramku pouze z toho, co Vision skutečně vidí.
    - dvě slova z vizuální analýzy
    - dvě emoji odpovídající motivu na fotce
    - žádné výchozí náhrady (bez fallbacků typu „Jemná“, „radost“)
    """
    tags = _normalize_bracelet_name_tags(vision_tags)
    desc = (description or "").lower()
    preferred = [t for t in tags if desc and t in desc]
    pool = preferred or tags

    rag_candidates: list[tuple[str, str]] = []
    if rag_pairs:
        rag_candidates.extend(rag_pairs)
    rag_from_text = _extract_two_words_from_rag_title(rag_text or "")
    if rag_from_text:
        rag_candidates.insert(0, rag_from_text)

    vision_adjs: list[str] = []
    for tag in pool:
        if tag in _COLOR_TAGS:
            vision_adjs.append(tag)
    for tag in pool:
        if tag in _STYLE_ADJ_BY_TAG:
            vision_adjs.append(_STYLE_ADJ_BY_TAG[tag])
    if not vision_adjs:
        for tag in pool:
            word = _pick_word_from_tag(tag, prefer_last=False)
            if word:
                vision_adjs.append(word)
                break

    vision_nouns: list[str] = []
    for tag in pool:
        if tag in _BRACELET_PRIMARY_MOTIF_TAGS:
            vision_nouns.append(tag)
    for tag in pool:
        if tag in _BRACELET_FALLBACK_MOTIF_TAGS:
            vision_nouns.append(tag)
    if not vision_nouns:
        for tag in pool:
            if tag in _BRACELET_DISALLOWED_SECOND_TAGS:
                continue
            word = _pick_word_from_tag(tag, prefer_last=True)
            if word:
                vision_nouns.append(word)
                break

    def _is_forbidden_word(w: str) -> bool:
        if not w:
            return True
        low = w.lower().strip()
        if low in _BRACELET_FORBIDDEN_TITLE_WORDS:
            return True
        return any(low.startswith(p) for p in _BRACELET_BANNED_WORD_PREFIXES)

    existing_pairs = _get_existing_title_pairs()
    for pair in rag_candidates:
        existing_pairs.add((pair[0].lower(), pair[1].lower()))

    first_raw = ""
    second_raw = ""
    # 1) PRVNÍ PRIORITA = vždy nejdřív pár z RAG (Chroma product_descriptions)
    for adj, noun in rag_candidates:
        if not adj or not noun:
            continue
        if _is_forbidden_word(adj) or _is_forbidden_word(noun):
            continue
        if _same_stem(adj, noun):
            continue
        first_raw, second_raw = adj, noun
        break
    # 2) DRUHÁ PRIORITA = teprve když RAG nic vhodného nemá → Vision z fotky (tagy z obrázku)
    vision_adj_pool = _dedupe([a for a in vision_adjs if a and not _is_forbidden_word(a)])
    vision_noun_pool = _dedupe([n for n in vision_nouns if n and not _is_forbidden_word(n)])
    if not first_raw or not second_raw:
        for adj in vision_adj_pool:
            for noun in vision_noun_pool:
                if not adj or not noun:
                    continue
                if _same_stem(adj, noun):
                    continue
                if _is_forbidden_word(adj) or _is_forbidden_word(noun):
                    continue
                key = (adj.lower(), noun.lower())
                if key in existing_pairs:
                    continue
                first_raw, second_raw = adj, noun
                break
            if first_raw and second_raw:
                break

    # Žádné doplňování: ne _pick_first_word, ne _pick_second_word, žádné pooly ani tagy.
    # Pokud RAG ani Vision nedaly pár → jen „Návrh názvu“ + emoji.
    first = _title_word(first_raw)
    second = _title_word(second_raw)

    # RAG ani Vision nedaly platný pár → jen „Návrh názvu“ + emoji (bez doplňování)
    if not first or not second:
        emojis = _pick_bracelet_emojis(pool or tags, rotation_index=rotation_index)
        emoji_pair = "".join(emojis) if emojis else ""
        return f"„Návrh názvu“ {emoji_pair}".strip()

    emojis = _pick_bracelet_emojis(pool or tags, rotation_index=rotation_index)
    emoji_pair = "".join(emojis) if emojis else ""
    return f"„{first} {second}“ {emoji_pair}".strip()


def _dedupe(items: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _pick_emoji_by_motif(tags: List[str]) -> str:
    """Vrátí emoji vhodné k motivu (podle tagů); jinak náhodné z EMOJI_DEFAULT_POOL."""
    tags_low = [str(t).lower().strip() for t in (tags or []) if t]
    for keyword, emoji in EMOJI_BY_MOTIF:
        for tag in tags_low:
            if keyword in tag:
                return emoji
    import random
    return random.choice(EMOJI_DEFAULT_POOL) if EMOJI_DEFAULT_POOL else "✨"


# Mapování tagů na krátké věty pro odrážky (nikdy ne výčet surových tagů)
_TAG_TO_BULLET_PHRASE: Dict[str, str] = {
    "náramek": "Elastický náramek s jemným provedením",
    "korálek": "Kulaté korálky",
    "korálky": "Korálkové provedení",
    "šperk": "Ruční šperk",
    "drahokam": "Drahokamové doplňky",
    "výroba šperků": "Ruční výroba",
    "přírodní materiál": "Přírodní materiály",
    "stříbrná": "Stříbrné detaily",
    "zlatá": "Zlaté detaily",
    "růžová": "Růžové tóny",
    "modrá": "Modré tóny",
    "zelená": "Zelené tóny",
    "černá": "Černé doplňky",
    "křišťál": "Křišťálové prvky",
    "sklo": "Skleněné provedení",
    "dekorace": "Dekorativní provedení",
}


def _tag_to_bullet_phrase(tag: str) -> str:
    t = (tag or "").strip().lower()
    return _TAG_TO_BULLET_PHRASE.get(t, (tag or "").capitalize() + " z fotografie")


def build_required_structure_from_vision(
    product_type: str,
    combined_tags: List[str],
    query_embedding: Optional[List[float]] = None,
) -> tuple[str, str]:
    """
    Jediný povolený fallback: vždy vrátí text ve POVINNÉ struktuře (✨ Popis produktu, 💎 Styl).
    Nikdy ne „Náramek – náramek“, nikdy ne výčet surových tagů. Vision vždy něco přečte – vždy vznikne text.
    """
    tags = _filter_tags(combined_tags or [])
    tags = [re.sub(r"\s*\(en\)\s*$", "", t, flags=re.I).strip() for t in tags if t and "(EN)" not in t]
    tags = _dedupe([t for t in tags if t])
    article = _pick_article(product_type, tags)
    article_low = article.lower()
    emoji = _pick_emoji_by_motif(tags)
    # Nikdy "X – X" (např. Náramek – náramek): první část musí být odlišná od druhé
    if tags and (tags[0].lower().strip() == article_low or tags[0].lower() == article_low):
        if len(tags) > 1:
            first_detail = _tag_to_bullet_phrase(tags[1]).split()[0].capitalize() if tags[1] else "Jemný"
        else:
            first_detail = "Jemný"
        title = f"{emoji} {first_detail} – {article}"
    else:
        first_detail = (tags[0].capitalize() if tags else "Jemný")
        title = f"{emoji} {first_detail} – {article}"
    # Popis: preferovat vzor z originálů (struktura), jinak odrážky z frází, NE surové tagy
    description = ""
    originál_text: Optional[str] = None
    if query_embedding:
        originál_text, _ = _find_best_original_fallback(query_embedding, product_type)
        if originál_text and "\n\n" in originál_text:
            description = originál_text.split("\n\n", 1)[1].strip()
            if not description:
                description = MANDATORY_STRUCTURE_TEMPLATE.split("\n\n", 1)[1].strip()
        else:
            originál_text = None
    if not description:
        phrase_bullets = [_tag_to_bullet_phrase(t) for t in tags[:5] if t and t.lower() != article_low]
        if not phrase_bullets:
            phrase_bullets = [f"{article.capitalize()} z fotografie – jemné provedení"]
        bullets = [f"- {p}" for p in phrase_bullets[:5]]
        style_words = [tags[i] for i in range(2, min(5, len(tags))) if tags[i] and tags[i].lower() != article_low]
        if not style_words:
            style_words = ["přírodní", "jemný"]
        style_str = ", ".join(style_words[:3])
        description = "✨ Popis produktu:\n" + "\n".join(bullets) + "\n\n💎 Styl: " + style_str
    return title, description


def _filter_tags(tags: List[str]) -> List[str]:
    cleaned: List[str] = []
    for tag in tags or []:
        raw = str(tag or "").strip()
        if not raw:
            continue
        low = raw.lower()
        if low in _GENERIC_TAGS:
            continue
        cleaned.append(raw)
    return _dedupe(cleaned)


def _pick_article(product_type: str, tags: List[str]) -> str:
    if product_type in _ARTICLE_BY_TYPE:
        return _ARTICLE_BY_TYPE[product_type]
    for tag in tags:
        if tag in _COLOR_TAGS or tag in _MATERIAL_TAGS:
            continue
        return tag
    return "dekorace"


def build_structured_fallback(product_type: str, combined_tags: List[str]) -> tuple[str, str]:
    tags = _filter_tags(combined_tags or [])
    tags = [t for t in tags if "(EN)" not in t]
    article = _pick_article(product_type, tags)

    colors = [t for t in tags if t in _COLOR_TAGS]
    materials = [t for t in tags if t in _MATERIAL_TAGS]
    product_words = [t for t in tags if t in VISION_TO_PRODUCT_TYPE]
    others = [t for t in tags if t not in colors and t not in materials and t not in product_words]

    def _display(tag: str) -> str:
        return re.sub(r"\s*\(en\)\s*$", "", tag, flags=re.I).strip()

    colors = [_display(t) for t in colors if _display(t)]
    materials = [_display(t) for t in materials if _display(t)]
    others = [_display(t) for t in others if _display(t)]

    emoji = random_emoji()
    if others:
        detail = ", ".join((colors[:1] + materials[:1])) if (colors or materials) else ""
        if detail:
            title = f"{others[0].capitalize()} – {article}, {detail} {emoji}"
        else:
            title = f"{others[0].capitalize()} – {article} {emoji}"
    elif colors or materials:
        key = ", ".join((colors[:2] or materials[:2]))
        title = f"{article.capitalize()} – {key} {emoji}"
    else:
        title = f"{article.capitalize()} {emoji}"

    sentences: List[str] = []
    if others:
        chunk = ", ".join(others[:3])
        sentences.append(f"Na fotografii je {article} s motivem {chunk}.")
    else:
        sentences.append(f"Na fotografii je {article}.")

    if colors and materials:
        sentences.append(f"Vynikají tóny {', '.join(colors[:2])} a materiál {', '.join(materials[:2])}.")
    elif colors:
        sentences.append(f"Převažují tóny {', '.join(colors[:2])}.")
    elif materials:
        sentences.append(f"Materiál působí jako {', '.join(materials[:2])}.")

    if len(sentences) < 2 and product_words:
        sentences.append(f"Motiv odpovídá typu: {', '.join(product_words[:1])}.")

    description = " ".join(sentences).strip()
    return title, description

def _fill_template(tpl: str, tags: List[str]) -> str:
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

def _get_rag_template(product_type: str) -> str:
    fallback = get_fallback_template(product_type)
    t1 = fallback.get("title_template", "")
    t2 = fallback.get("description_template", "")
    return f"{t1}\n\n{t2}" if t1 or t2 else f"Vzor pro {product_type} – použij strukturu a styl."

RAG_DISTANCE_THRESHOLD = 0.25
FALLBACK_EMBEDDING_DIM = 384

# Cache embeddingů pro 8 originál vzorů (aby se nepočítaly při každém requestu)
_original_fallback_embeddings: List[tuple[str, List[float], str]] | None = None


def _get_original_fallback_embeddings() -> List[tuple[str, List[float], str]]:
    """Vrátí seznam (full_text, embedding, product_type) pro 8 originál vzorů. Jednou načtené cachuje."""
    global _original_fallback_embeddings
    if _original_fallback_embeddings is not None:
        return _original_fallback_embeddings
    try:
        from .embeddings import embed_text
    except Exception:
        return []
    out: List[tuple[str, List[float], str]] = []
    for title, desc, ptype in ORIGINAL_FALLBACK_TEMPLATES:
        text = f"{title}\n\n{desc}"
        emb = embed_text(text)
        if emb:
            out.append((text, emb, ptype))
    _original_fallback_embeddings = out
    return out


def _find_best_original_fallback(
    query_embedding: List[float],
    product_type: str | None = None,
) -> tuple[str | None, float | None]:
    """
    Vybere nejvhodnější z 8 fixních originál vzorů podle podobnosti (L2 distance).
    product_type může zužovat výběr – preferují se vzory stejného typu.
    """
    items = _get_original_fallback_embeddings()
    if not items or not query_embedding:
        return None, None
    best_text = None
    best_dist: float | None = None
    for text, emb, ptype in items:
        if product_type and ptype != product_type:
            continue
        try:
            dist = sum((a - b) ** 2 for a, b in zip(query_embedding, emb)) ** 0.5
        except Exception:
            continue
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_text = text
    if best_text:
        return best_text, best_dist
    # Žádná shoda podle product_type – vezmi nejbližší bez filtru
    for text, emb, _ in items:
        try:
            dist = sum((a - b) ** 2 for a, b in zip(query_embedding, emb)) ** 0.5
        except Exception:
            continue
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_text = text
    return best_text, best_dist


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_query_text(
    product_type: str,
    combined_tags: List[str],
    raw_tags: List[str] | None = None,
) -> str:
    tags = [t.strip() for t in (combined_tags or []) if t and str(t).strip()]
    tags = list(dict.fromkeys(tags))
    if not tags and raw_tags:
        raw = [t.strip() for t in raw_tags if t and str(t).strip()]
        tags = list(dict.fromkeys(raw))
    if tags:
        return f"{product_type} | " + ", ".join(tags)
    return product_type


def get_best_rag_template(
    vision_tags: List[str],
    product_type: str | None = None,
    require_structure: bool = True,
) -> str:
    """
    Vrátí jeden (top1) nejpodobnější vzor z RAG (Chroma) podle Vision tagů.
    Pokud nic nenajde, vrací prázdný string.
    require_structure=True ponechá jen šablony s ✨ Popis produktu a 💎 Styl.
    """
    tags = [str(t).strip() for t in (vision_tags or []) if str(t).strip()]
    tags = list(dict.fromkeys(tags))
    query_text = " ".join(tags).strip()
    if not query_text:
        logger.info("RAG top1 search found=0 using_top1=")
        return ""

    try:
        from .embeddings import embed_text
        from .chroma_client import search
    except Exception:
        return ""

    try:
        query_embedding = embed_text(query_text)
    except Exception:
        return ""
    if not query_embedding:
        return ""

    try:
        where = {"product_type": product_type} if product_type else None
        result = search(query_embedding=query_embedding, n_results=1, where=where)
    except Exception:
        return ""

    docs = (result or {}).get("documents") or []
    doc_list = docs[0] if docs else []
    count = len(doc_list) if isinstance(doc_list, list) else 0
    top1 = doc_list[0] if count > 0 else None
    top1_text = str(top1).strip() if top1 else ""
    preview = (top1_text.replace("\n", " ")[:60] if top1_text else "")
    logger.info("RAG top1 search found=%s using_top1=%s", count, preview)
    if not top1_text:
        return ""
    if require_structure:
        has_required_structure = (
            "✨" in top1_text
            and "Popis produktu" in top1_text
            and "💎" in top1_text
            and "Styl" in top1_text
        )
        if not has_required_structure:
            logger.info("RAG top1 missing required structure, ignoring template")
            return ""
    return top1_text


def get_rag_title_pairs(
    vision_tags: List[str],
    product_type: str | None = None,
    n_results: int = 5,
) -> list[tuple[str, str]]:
    tags = [str(t).strip() for t in (vision_tags or []) if str(t).strip()]
    tags = list(dict.fromkeys(tags))
    query_text = " ".join(tags).strip()
    if not query_text:
        return []
    try:
        from .embeddings import embed_text
        from .chroma_client import search
    except Exception:
        return []
    try:
        query_embedding = embed_text(query_text)
    except Exception:
        return []
    if not query_embedding:
        return []
    try:
        where = {"product_type": product_type} if product_type else None
        result = search(query_embedding=query_embedding, n_results=n_results, where=where)
    except Exception:
        return []
    docs = (result or {}).get("documents") or []
    doc_list = docs[0] if docs else []
    pairs: list[tuple[str, str]] = []
    if isinstance(doc_list, list):
        for doc in doc_list:
            pair = _extract_two_words_from_rag_title(str(doc))
            if pair:
                pairs.append(pair)
    return pairs


def _parse_product_template_doc(doc: str) -> str | None:
    """Převádí dokument z product_templates (TITLE:/DESCRIPTION:) na formát pro LLM."""
    if not doc or not doc.strip():
        return None
    title = None
    desc = None
    for line in (doc or "").splitlines():
        line = line.strip()
        if line.upper().startswith("TITLE:"):
            title = line[6:].strip()
        elif line.upper().startswith("DESCRIPTION:"):
            desc = line[12:].strip()
    if title and desc:
        return f"{title}\n\n{desc}"
    return doc.strip() if doc.strip() else None


def _find_similar_rag_template(
    product_type: str,
    combined_tags: List[str],
    raw_tags: List[str] | None = None,
) -> tuple[str | None, float | None, str, List[float]]:
    query_text = _build_query_text(product_type, combined_tags, raw_tags)
    try:
        from .embeddings import embed_text
        from .chroma_client import search
    except Exception:
        return None, None, query_text, []

    try:
        query_embedding = embed_text(query_text)
    except Exception:
        return None, None, query_text, []
    if not query_embedding:
        return None, None, query_text, []

    # 1) Nejdříve hledáme v product_templates (admin šablony – reálné produkty, náramky)
    try:
        from app.modules.ai.templates.repository import search_templates
        pt_result = search_templates(
            query_text,
            product_type=product_type,
            n_results=5,
        )
    except Exception:
        pt_result = None

    if pt_result:
        docs = (pt_result or {}).get("documents") or []
        dists = (pt_result or {}).get("distances") or []
        doc_list = docs[0] if docs else []
        dist_list = dists[0] if dists else []
        best_pt_template = None
        best_pt_distance = None
        for doc, dist in zip(doc_list, dist_list):
            if not doc or dist is None:
                continue
            try:
                dist_val = float(dist)
            except (TypeError, ValueError):
                continue
            parsed = _parse_product_template_doc(str(doc))
            if parsed and (best_pt_distance is None or dist_val < best_pt_distance):
                best_pt_template = parsed
                best_pt_distance = dist_val
        if best_pt_template:
            return best_pt_template, best_pt_distance, query_text, query_embedding

    # 2) Fallback: product_descriptions (seed šablony)
    try:
        result = search(
            query_embedding=query_embedding,
            n_results=5,
            where={"product_type": product_type},
        )
    except Exception:
        return None, None, query_text, query_embedding

    docs = (result or {}).get("documents") or []
    dists = (result or {}).get("distances") or []
    doc_list = docs[0] if docs else []
    dist_list = dists[0] if dists else []

    best_template = None
    best_distance = None
    for doc, dist in zip(doc_list, dist_list):
        if not doc or dist is None:
            continue
        try:
            dist_val = float(dist)
        except (TypeError, ValueError):
            continue
        if best_distance is None or dist_val < best_distance:
            best_distance = dist_val
            best_template = str(doc).strip()

    return best_template, best_distance, query_text, query_embedding


def _save_rag_template(
    *,
    product_type: str,
    title: str,
    description: str,
    query_embedding: List[float],
    query_text: str,
    combined_tags: List[str],
    raw_tags: List[str] | None = None,
    vision_tags_cz: List[str] | None = None,
) -> bool:
    embedding = query_embedding or ([0.0] * FALLBACK_EMBEDDING_DIM)
    text = f"{title}\n\n{description}".strip()
    if not text:
        return False
    try:
        from .chroma_client import add_document
        add_document(
            doc_id=f"auto_{product_type}_{uuid.uuid4().hex}",
            text=text,
            embedding=embedding,
            metadata={
                "product_type": product_type,
                "timestamp": _utc_now_iso(),
                "raw_tags": raw_tags or [],
                "vision_tags_cz": vision_tags_cz or [],
                "source": "auto",
                "query_text": query_text,
                "tags": ", ".join(combined_tags or []),
            },
        )
        return True
    except Exception:
        return False


def _get_title_and_description(
    product_type: str,
    combined_tags: List[str],
    raw_tags: List[str] | None = None,
    vision_tags_cz: List[str] | None = None,
    ai_template_text: str | None = None,
) -> tuple:
    if ai_template_text is None:
        try:
            from app.modules.ai.templates.service import load_ai_template_from_db
            ai_template_text = load_ai_template_from_db(
                product_type=product_type,
                combined_tags=combined_tags,
            )
        except Exception:
            ai_template_text = None

    normalized_vision_tags = vision_tags_cz if vision_tags_cz is not None else combined_tags
    best_template = get_best_rag_template(normalized_vision_tags, product_type)
    best_template_used = bool(best_template)
    has_match = best_template_used
    distance = 0.0 if best_template_used else None

    query_text = " ".join([str(t).strip() for t in (normalized_vision_tags or []) if str(t).strip()]).strip()
    query_embedding: List[float] = []
    if query_text:
        try:
            from .embeddings import embed_text
            query_embedding = embed_text(query_text) or []
        except Exception:
            query_embedding = []
    used_original_fallback = False
    original_fallback_text: str | None = None
    if best_template_used:
        rag_template = best_template
        use_mandatory_structure = False
    else:
        # Best template chybí → použij top-1 z ORIGINAL_FALLBACK_TEMPLATES podle embeddingu
        originál_text, _ = _find_best_original_fallback(query_embedding, product_type)
        used_original_fallback = bool(originál_text)
        original_fallback_text = originál_text
        if originál_text:
            rag_template = originál_text
            use_mandatory_structure = False
        else:
            rag_template = MANDATORY_STRUCTURE_TEMPLATE
            use_mandatory_structure = True
    if not rag_template or not rag_template.strip():
        rag_template = MANDATORY_STRUCTURE_TEMPLATE
        use_mandatory_structure = True
        used_original_fallback = False

    rag_meta = {
        "rag_matched": bool(has_match),
        "rag_distance": distance,
        "rag_threshold": RAG_DISTANCE_THRESHOLD,
        "rag_status": "adapted" if has_match else ("originál_fallback" if used_original_fallback else "new_saved"),
        "rag_saved": False,
    }

    if rag_template and rag_template != MANDATORY_STRUCTURE_TEMPLATE:
        logger.info("RAG originál fallback used product_type=%s", product_type)
    else:
        logger.info("RAG no template product_type=%s using mandatory structure", product_type)
    try:
        from .llm_client import generate_product_description
        llm_tags = vision_tags_cz if vision_tags_cz is not None else combined_tags
        result = generate_product_description(
            vision_tags_cz=llm_tags,
            product_type=product_type,
            rag_template=rag_template,
            prefer_vision_title=use_mandatory_structure,
            vision_raw_tags=None,
            use_mandatory_structure=use_mandatory_structure,
        )
        if result and result[0] and result[1]:
            if not has_match:
                saved = _save_rag_template(
                    product_type=product_type,
                    title=result[0],
                    description=result[1],
                    query_embedding=query_embedding,
                    query_text=query_text,
                    combined_tags=combined_tags,
                    raw_tags=raw_tags,
                    vision_tags_cz=vision_tags_cz,
                )
                rag_meta["rag_saved"] = bool(saved)
                rag_meta["rag_status"] = "new_saved" if saved else "new_failed"
            return result[0], result[1], rag_meta
    except Exception:
        pass
    if used_original_fallback and original_fallback_text:
        llm_available = True
        try:
            from .llm_client import _get_llm_client
            llm_available = bool(_get_llm_client())
        except Exception:
            llm_available = False

        if llm_available:
            parts = original_fallback_text.split("\n\n", 1)
            title = parts[0].strip() if parts else ""
            description = parts[1].strip() if len(parts) > 1 else ""
            if title and description:
                return title, description, rag_meta

    title, description = build_required_structure_from_vision(
        product_type, combined_tags, query_embedding=query_embedding
    )
    if not has_match:
        saved = _save_rag_template(
            product_type=product_type,
            title=title,
            description=description,
            query_embedding=query_embedding,
            query_text=query_text,
            combined_tags=combined_tags,
            raw_tags=raw_tags,
            vision_tags_cz=vision_tags_cz,
        )
        rag_meta["rag_saved"] = bool(saved)
        rag_meta["rag_status"] = "new_saved" if saved else "new_failed"
    return title, description, rag_meta

def generate_drafts_for_session(product_id: Union[int, str]) -> Dict[str, Any]:
    media_assets = get_media_assets_by_session(product_id)
    all_tags: List[str] = []
    all_raw_tags: List[str] = []
    all_vision_tags_cz: List[str] = []
    for asset in media_assets:
        try:
            vision_result = analyze_image_with_vision(asset.path_original)
            raw_tags = normalize_tags(vision_result)
            print(f"[VISION RAW TAGS] product_id={product_id}, file={asset.path_original}: {raw_tags}")
            tags_cz_full = translate_tags_to_czech(raw_tags)
            asset.tags = tags_cz_full
            all_tags.extend(tags_cz_full)
            all_vision_tags_cz.extend(tags_cz_full)
            all_raw_tags.extend(raw_tags or [])
        except Exception as e:
            print(f"[VISION ERROR] {asset.path_original}: {e}")
    product_type = detect_product_type(all_tags)
    combined_tags = list(dict.fromkeys(all_tags))
    title, description, rag_meta = _get_title_and_description(
        product_type,
        combined_tags,
        raw_tags=all_raw_tags,
        vision_tags_cz=all_vision_tags_cz,
    )
    if title and not _contains_emoji(title):
        title = f"{random_emoji()} {title}"
    suggested_price = None
    seo_title = None
    seo_description = None
    seo_keywords = None
    try:
        from app.modules.ai.templates.service import suggest_price

        suggested_price = suggest_price(product_type=product_type, combined_tags=combined_tags)
    except Exception:
        suggested_price = None
    try:
        clean_title = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", title or "").strip()
        clean_desc = " ".join((description or "").replace("\n", " ").split())
        seo_title = (clean_title or title or None)
        seo_description = clean_desc[:155] + ("…" if clean_desc and len(clean_desc) > 155 else "")
        seo_keywords = ", ".join(combined_tags[:10]) if combined_tags else None
    except Exception:
        pass
    return {
        "session_id": str(product_id),
        "product_type": product_type,
        "image_count": len(media_assets),
        "combined_tags": combined_tags,
        "title": title,
        "description": description,
        "suggested_price_czk": suggested_price,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "seo_keywords": seo_keywords,
        **rag_meta,
    }

def generate_drafts_for_variant(variant_id: Union[int, str]) -> Dict[str, Any]:
    from .media_repository import get_media_assets_for_variant
    media_assets = get_media_assets_for_variant(variant_id)
    all_tags: List[str] = []
    all_raw_tags: List[str] = []
    all_vision_tags_cz: List[str] = []
    for asset in media_assets:
        try:
            vision_result = analyze_image_with_vision(asset.path_original)
            raw_tags = normalize_tags(vision_result)
            print(f"[VISION RAW TAGS] variant_id={variant_id}, file={asset.path_original}: {raw_tags}")
            tags_cz_full = translate_tags_to_czech(raw_tags)
            asset.tags = tags_cz_full
            all_tags.extend(tags_cz_full)
            all_vision_tags_cz.extend(tags_cz_full)
            all_raw_tags.extend(raw_tags or [])
        except Exception as e:
            print(f"[VISION ERROR] {asset.path_original}: {e}")
    product_type = detect_product_type(all_tags)
    combined_tags = list(dict.fromkeys(all_tags))
    title, description, rag_meta = _get_title_and_description(
        product_type,
        combined_tags,
        raw_tags=all_raw_tags,
        vision_tags_cz=all_vision_tags_cz,
    )
    if title and not _contains_emoji(title):
        title = f"{random_emoji()} {title}"
    suggested_price = None
    seo_title = None
    seo_description = None
    seo_keywords = None
    try:
        from app.modules.ai.templates.service import suggest_price

        suggested_price = suggest_price(product_type=product_type, combined_tags=combined_tags)
    except Exception:
        suggested_price = None
    try:
        clean_title = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", title or "").strip()
        clean_desc = " ".join((description or "").replace("\n", " ").split())
        seo_title = (clean_title or title or None)
        seo_description = clean_desc[:155] + ("…" if clean_desc and len(clean_desc) > 155 else "")
        seo_keywords = ", ".join(combined_tags[:10]) if combined_tags else None
    except Exception:
        pass
    return {
        "session_id": str(variant_id),
        "product_type": product_type,
        "image_count": len(media_assets),
        "combined_tags": combined_tags,
        "title": title,
        "description": description,
        "suggested_variant_price_czk": suggested_price,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "seo_keywords": seo_keywords,
        **rag_meta,
    }


# =========================
# NOVÝ FILTR VIZUÁLNÍCH TAGŮ
# =========================

FORBIDDEN_NON_VISUAL = {
    "ruční tvorba","ruční práce","ruční zpracování",
    "jemný design","příjemná barva","precizní detail",
    "klidná atmosféra","vhodné jako dárek","stylový produkt",
}

def filter_visual_tags(tags):
    cleaned = []
    for t in tags or []:
        t_low = t.lower().strip()

        if any(bad in t_low for bad in FORBIDDEN_NON_VISUAL):
            continue

        if (
            t_low in _COLOR_TAGS
            or t_low in _MATERIAL_TAGS
            or t_low in VISION_TO_PRODUCT_TYPE
            or "korálek" in t_low
            or "šňůrka" in t_low
            or "elast" in t_low
            or "povrch" in t_low
        ):
            cleaned.append(t)

    return cleaned
