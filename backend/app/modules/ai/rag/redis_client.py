# -*- coding: utf-8 -*-
"""
In-memory cache místo Redis (Redis v projektu není).
Všechna volání set_cache/get_cache pracují s Python dict.
"""
import json
from typing import Any, Optional

# Jednoduchý in-memory cache (klíč -> (value_json, expiry neřešíme pro jednoduchost)
_cache: dict = {}


def get_redis():
    """
    Redis v projektu není. Tato funkce existuje pro kompatibilitu.
    Při použití vyhodí NotImplementedError – používejte set_cache/get_cache.
    """
    raise NotImplementedError("Redis není k dispozici. Použijte set_cache/get_cache.")


def set_cache(key: str, value: Any, ttl: int = 3600) -> None:
    """
    Uloží hodnotu do in-memory cache.
    key: unikátní klíč, value: JSON-serializovatelný objekt, ttl: ignorován.
    """
    try:
        _cache[key] = json.dumps(value)
    except TypeError:
        _cache[key] = value


def get_cache(key: str) -> Optional[Any]:
    """
    Načte hodnotu z in-memory cache. Pokud klíč neexistuje, vrací None.
    """
    if key not in _cache:
        return None
    raw = _cache[key]
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return raw
    return raw
