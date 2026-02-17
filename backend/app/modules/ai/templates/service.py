# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from app.core.pricing_rules import (
    BRACELET_BASE_PRICE_CZK,
    BRACELET_PENDANT_PRICE_CZK,
    infer_bracelet_price_czk,
)
from app.db.models import Product
from app.modules.ai.rag.seed_templates import _get_product_type_from_category

from .repository import add_template, list_templates, search_templates, upsert_template

PRICE_DISTANCE_THRESHOLD = float(os.getenv("TEMPLATE_PRICE_DISTANCE_THRESHOLD", "0.6"))
BRACELET_PRICE_RULES = (
    {
        "id": "system_price_rule_bracelet_no_pendant_v1",
        "title": "Systémové pravidlo: náramek bez přívěšku",
        "text": (
            "CENOVÉ PRAVIDLO: Náramek bez přívěsku / bez přívěšku má cenu 149 CZK. "
            "Platí pro bracelet bez pendant/charm."
        ),
        "price_czk": BRACELET_BASE_PRICE_CZK,
    },
    {
        "id": "system_price_rule_bracelet_with_pendant_v1",
        "title": "Systémové pravidlo: náramek s přívěškem",
        "text": (
            "CENOVÉ PRAVIDLO: Náramek s přívěskem / s přívěškem má cenu 159 CZK. "
            "Platí pro bracelet s pendant/charm."
        ),
        "price_czk": BRACELET_PENDANT_PRICE_CZK,
    },
)


def _build_template_text(
    *,
    title: str,
    description: str,
    product_type: str,
    price_czk: Optional[float],
) -> str:
    return (
        f"TITLE: {title}\n"
        f"DESCRIPTION: {description}\n"
        f"PRODUCT_TYPE: {product_type}\n"
        f"PRICE_CZK: {price_czk if price_czk is not None else 'N/A'}"
    )


def store_template_for_product(db, product_id: int) -> dict[str, Any]:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError("Product not found")

    title = (product.name or "").strip()
    description = (product.description or "").strip()
    if not title or not description:
        raise ValueError("Product must have name and description")

    product_type = (
        _get_product_type_from_category(getattr(product, "category", None))
        if getattr(product, "category", None)
        else "other"
    )
    price_czk = float(product.price_czk) if product.price_czk is not None else None

    created_at = datetime.now(timezone.utc).isoformat()
    doc_id = f"tpl_{product.id}_{uuid.uuid4().hex[:8]}"
    text = _build_template_text(
        title=title,
        description=description,
        product_type=product_type,
        price_czk=price_czk,
    )
    metadata = {
        "product_id": product.id,
        "title": title,
        "product_type": product_type,
        "price_czk": price_czk,
        "created_at": created_at,
    }

    add_template(doc_id, text, metadata)
    return {"id": doc_id, **metadata}


def list_template_items() -> list[dict[str, Any]]:
    items = list_templates()
    # drop document field in response to keep payload light
    for item in items:
        item.pop("document", None)
    return items


def suggest_price(
    *,
    product_type: str,
    combined_tags: list[str],
) -> Optional[float]:
    rule_price = infer_bracelet_price_czk(
        product_type=product_type,
        tags=combined_tags,
    )
    if rule_price is not None:
        return float(rule_price)

    query_text = f"{product_type}\n{', '.join(combined_tags or [])}".strip()
    result = search_templates(query_text, product_type=product_type, n_results=1)
    if not result:
        return None
    distances = result.get("distances") or []
    metadatas = result.get("metadatas") or []
    if not distances or not metadatas or not distances[0] or not metadatas[0]:
        return None
    distance = distances[0][0] if distances[0] else None
    meta = metadatas[0][0] if metadatas[0] else None
    if distance is None or meta is None:
        return None
    if distance > PRICE_DISTANCE_THRESHOLD:
        return None
    price = meta.get("price_czk") if isinstance(meta, dict) else None
    try:
        return float(price) if price is not None else None
    except (TypeError, ValueError):
        return None


def seed_bracelet_price_rules_to_chroma() -> dict[str, bool]:
    outcomes: dict[str, bool] = {}
    now = datetime.now(timezone.utc).isoformat()
    for rule in BRACELET_PRICE_RULES:
        rule_id = str(rule["id"])
        try:
            upsert_template(
                doc_id=rule_id,
                text=str(rule["text"]),
                metadata={
                    "title": str(rule["title"]),
                    "product_type": "bracelet",
                    "price_czk": float(rule["price_czk"]),
                    "system_rule": True,
                    "created_at": now,
                },
            )
            outcomes[rule_id] = True
        except Exception:
            outcomes[rule_id] = False
    return outcomes


def load_ai_template_from_db(
    *,
    product_type: str,
    combined_tags: list[str],
) -> Optional[str]:
    """
    Vrátí text existující AI Template (Systém B) jako stylový vzor.
    Pokud nic nenajde, vrací None.
    """
    query_text = f"{product_type}\n{', '.join(combined_tags or [])}".strip()
    result = search_templates(query_text, product_type=product_type, n_results=1)
    if not result:
        return None
    docs = result.get("documents") or []
    if not docs or not docs[0] or not docs[0][0]:
        return None
    doc = docs[0][0]
    return doc.strip() if isinstance(doc, str) and doc.strip() else None
