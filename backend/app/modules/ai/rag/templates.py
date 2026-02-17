# -*- coding: utf-8 -*-
# Výchozí systémové šablony (fallback)
# Použijí se pouze pokud nejsou žádné šablony v DB / Chroma.

bracelet_template = {
    "title_template": "Náramek – {hlavni_atribut} ✨",
    "description_template": (
        "✨ Popis produktu:\n"
        "- Viditelné prvky: {motiv}\n"
        "- Barevné tóny: {barva}\n"
        "- Materiál / detail: {klíčový_detail}\n"
        "\n"
        "💎 Styl: {barva}, {hlavni_atribut}, {motiv}"
    ),
    "product_type": "bracelet",
    "style": "romantic",
    "tone": "jemný"
}

candle_template = {
    "title_template": "Svíčka – {atmosfera} 🕯️",
    "description_template": (
        "✨ Popis produktu:\n"
        "- Viditelné prvky: {motiv}\n"
        "- Barevné tóny: {barva}\n"
        "- Materiál / detail: {klíčový_detail}\n"
        "\n"
        "💎 Styl: {barva}, {atmosfera}, {motiv}"
    ),
    "product_type": "candle",
    "style": "minimalist",
    "tone": "klidný"
}

generic_template = {
    "title_template": "Dekorace – {hlavni_atribut} ✨",
    "description_template": (
        "✨ Popis produktu:\n"
        "- Viditelné prvky: {motiv}\n"
        "- Barevné tóny: {barva}\n"
        "- Materiál / detail: {klíčový_detail}\n"
        "\n"
        "💎 Styl: {barva}, {hlavni_atribut}, {motiv}"
    ),
    "product_type": "other",
    "style": "neutral",
    "tone": "informativní"
}


def get_fallback_template(product_type: str):
    """
    Vrátí fallback šablonu podle typu produktu.
    Pro bracelet/candle konkrétní šablonu, jinak generic.
    """
    if product_type == "bracelet":
        return bracelet_template
    if product_type == "candle":
        return candle_template
    return generic_template
