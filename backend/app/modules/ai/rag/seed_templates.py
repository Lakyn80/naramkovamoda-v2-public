# -*- coding: utf-8 -*-
"""
KROK 1 – Načtení referenčních šablon z DB do Chroma (RAG).

Pro každou hlavní kategorii (bracelet, candle, necklace, earrings, decor, other)
vybere JEDEN reálný produkt z databáze a uloží jeho název + popis jako vzor do Chroma.

doc_id = "template_<kategorie>"
text = celý název + celý popis (tak jak je v DB)
metadata = {"product_type": "<kategorie>"}
"""

from typing import Dict, List, Optional, Tuple

# Mapování názvu/slugu kategorie na product_type
CATEGORY_TO_PRODUCT_TYPE: Dict[str, str] = {
    "náramek": "bracelet",
    "náramky": "bracelet",
    "bracelet": "bracelet",
    "svíčka": "candle",
    "svíčky": "candle",
    "candle": "candle",
    "náhrdelník": "necklace",
    "náhrdelníky": "necklace",
    "necklace": "necklace",
    "náušnice": "earrings",
    "earrings": "earrings",
    "dekorace": "decor",
    "dekor": "decor",
    "decor": "decor",
}


def _category_to_product_type(category_name: Optional[str], category_slug: Optional[str]) -> str:
    """Mapuje název/slug kategorie na product_type."""
    for key, val in CATEGORY_TO_PRODUCT_TYPE.items():
        n = (category_name or "").lower()
        s = (category_slug or "").lower()
        if key in n or key in s:
            return val
    return "other"


def _get_product_type_from_category(category) -> str:
    return _category_to_product_type(
        getattr(category, "name", None),
        getattr(category, "slug", None),
    )


def _collect_products_by_type(db) -> Dict[str, Tuple[str, str]]:
    """
    Projde produkty v DB, seskupí podle product_type (z kategorie).
    Pro každý typ vrátí (název, popis) prvního produktu s vyplněným názvem i popisem.
    """
    from sqlalchemy.orm import selectinload
    from app.db.models import Product, Category

    result: Dict[str, Tuple[str, str]] = {}
    products = (
        db.query(Product)
        .options(selectinload(Product.category))
        .filter(Product.name.isnot(None), Product.name != "")
        .filter(Product.description.isnot(None), Product.description != "")
        .all()
    )

    for p in products:
        cat = getattr(p, "category", None)
        pt = _get_product_type_from_category(cat) if cat else "other"
        if pt not in result:
            name = (p.name or "").strip()
            desc = (p.description or "").strip()
            if name and desc:
                result[pt] = (name, desc)

    return result


def seed_rag_templates_from_db() -> Dict[str, bool]:
    """
    Pro každou hlavní kategorii načte jeden reálný produkt z DB
    a uloží ho do Chroma jako šablonu (template_<kategorie>).

    Vrací slovník {product_type: True/False} podle úspěchu.
    """
    from app.db.session import get_db
    from .chroma_client import add_document, get_collection
    from .embeddings import embed_text

    db = next(get_db())
    try:
        products_by_type = _collect_products_by_type(db)
    finally:
        db.close()

    # Zajistíme alespoň fallback pro typy bez produktu v DB
    all_types = ["bracelet", "candle", "necklace", "earrings", "decor", "other"]
    outcomes: Dict[str, bool] = {}

    for pt in all_types:
        if pt in products_by_type:
            name, desc = products_by_type[pt]
            text = f"{name}\n\n{desc}"
        else:
            # Fallback – prázdná šablona, RAG ji nepřepíše fakty z Vision
            text = f"Vzor pro {pt} – použij strukturu a styl, obsah vždy z Vision."
            name, desc = f"Produkt {pt}", text

        doc_id = f"template_{pt}"
        try:
            embedding = embed_text(text)
            add_document(
                doc_id=doc_id,
                text=text,
                embedding=embedding,
                metadata={"product_type": pt},
            )
            outcomes[pt] = True
        except Exception as e:
            outcomes[pt] = False
            print(f"[SEED ERROR] {doc_id}: {e}")

    # Seed deterministic bracelet pricing rules into product_templates collection (Chroma).
    try:
        from app.modules.ai.templates.service import seed_bracelet_price_rules_to_chroma

        rule_outcomes = seed_bracelet_price_rules_to_chroma()
        for rule_id, status in rule_outcomes.items():
            outcomes[f"pricing:{rule_id}"] = bool(status)
    except Exception:
        outcomes["pricing:seed_failed"] = False

    return outcomes
