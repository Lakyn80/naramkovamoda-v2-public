from __future__ import annotations

import unicodedata
from typing import Iterable, Optional

BRACELET_BASE_PRICE_CZK = 149.0
BRACELET_PENDANT_PRICE_CZK = 159.0

_BRACELET_KEYWORDS = (
    "naram",
    "bracelet",
)
_PENDANT_KEYWORDS = (
    "privesek",
    "priveskem",
    "privesku",
    "privesk",
    "pendant",
    "charm",
)
_NO_PENDANT_PATTERNS = (
    "bez prives",
    "without pendant",
    "no pendant",
    "bez charm",
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only.strip().lower()


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    if not haystack:
        return False
    return any(n in haystack for n in needles)


def infer_bracelet_price_czk(
    *,
    product_type: str | None = None,
    category_name: str | None = None,
    category_slug: str | None = None,
    title: str | None = None,
    description: str | None = None,
    tags: Optional[Iterable[str]] = None,
) -> float | None:
    """Return deterministic CZK price for bracelet rules, otherwise None."""
    normalized_product_type = _normalize_text(product_type)
    is_bracelet = normalized_product_type == "bracelet"

    context_parts = [
        _normalize_text(category_name),
        _normalize_text(category_slug),
        _normalize_text(title),
        _normalize_text(description),
    ]
    if tags:
        context_parts.extend(_normalize_text(t) for t in tags if t is not None)
    context = " ".join(part for part in context_parts if part)

    if not is_bracelet and _contains_any(context, _BRACELET_KEYWORDS):
        is_bracelet = True
    if not is_bracelet:
        return None

    has_pendant = _contains_any(context, _PENDANT_KEYWORDS)
    if has_pendant and _contains_any(context, _NO_PENDANT_PATTERNS):
        has_pendant = False
    return BRACELET_PENDANT_PRICE_CZK if has_pendant else BRACELET_BASE_PRICE_CZK
