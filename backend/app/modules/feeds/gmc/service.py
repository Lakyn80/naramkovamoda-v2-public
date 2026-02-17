# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import unicodedata
from typing import Iterable, Optional
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace

from app.db.models import Product


GNS = "http://base.google.com/ns/1.0"
register_namespace("g", GNS)


def _slugify(value: str) -> str:
    s = (value or "").lower().strip()
    try:
        s = unicodedata.normalize("NFD", s)
        s = "".join(ch for ch in s if not (0x300 <= ord(ch) <= 0x36F))
    except Exception:
        pass
    s = s.replace("\"", " ").replace("'", " ").replace("`", " ")
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug or "produkt"


def _base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://localhost:3002").rstrip("/")


def _api_base_url() -> str:
    return os.getenv("PUBLIC_API_BASE_URL", _base_url()).rstrip("/")


def _to_abs_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("/"):
        return f"{_api_base_url()}{path}"
    return f"{_api_base_url()}/static/uploads/{path}"


def _price_ok(value: Optional[float]) -> bool:
    if value is None:
        return False
    try:
        return float(value) > 0
    except Exception:
        return False


def _availability(stock: Optional[int]) -> str:
    try:
        return "in_stock" if int(stock or 0) > 0 else "out_of_stock"
    except Exception:
        return "out_of_stock"


def _add_text(parent: Element, tag: str, text: Optional[str]) -> None:
    if text is None:
        return
    el = SubElement(parent, tag)
    el.text = str(text)


def _g(parent: Element, tag: str, text: Optional[str]) -> None:
    if text is None:
        return
    el = SubElement(parent, f"{{{GNS}}}{tag}")
    el.text = str(text)


def _product_link(product: Product) -> str:
    slug = _slugify(product.name or "")
    return f"{_base_url()}/products/{slug}"


def build_gmc_feed(products: Iterable[Product]) -> str:
    rss = Element("rss", attrib={"version": "2.0", "xmlns:g": GNS})
    channel = SubElement(rss, "channel")
    _add_text(channel, "title", "Náramková Móda")
    _add_text(channel, "link", _base_url())
    _add_text(channel, "description", "Produktový feed pro Google Merchant Center")

    for product in products:
        if not product.name:
            continue
        price_val = float(product.price_czk) if product.price_czk is not None else None
        if not _price_ok(price_val):
            continue
        image_url = _to_abs_url(
            f"/static/uploads/{product.image}" if product.image else None
        )
        if not image_url:
            continue

        item = SubElement(channel, "item")
        _g(item, "id", str(product.id))
        _g(item, "title", product.seo_title or product.name)
        desc = product.seo_description or (product.description or "")
        _g(item, "description", desc)
        _g(item, "link", _product_link(product))
        _g(item, "image_link", image_url)
        _g(item, "availability", _availability(product.stock))
        _g(item, "price", f"{price_val:.2f} CZK")

        # Variant entries (only if variant has its own price)
        for variant in list(product.variants or []):
            v_price = float(variant.price_czk) if variant.price_czk is not None else None
            if not _price_ok(v_price):
                continue
            v_item = SubElement(channel, "item")
            _g(v_item, "id", f"{product.id}-{variant.id}")
            title = variant.variant_name or product.name
            _g(v_item, "title", title)
            _g(v_item, "description", variant.description or desc)
            _g(v_item, "link", f"{_product_link(product)}?variant={variant.id}")
            v_img = _to_abs_url(
                f"/static/uploads/{variant.image}" if variant.image else None
            ) or image_url
            _g(v_item, "image_link", v_img)
            _g(v_item, "availability", _availability(variant.stock))
            _g(v_item, "price", f"{v_price:.2f} CZK")

    return tostring(rss, encoding="utf-8", xml_declaration=True).decode("utf-8")
