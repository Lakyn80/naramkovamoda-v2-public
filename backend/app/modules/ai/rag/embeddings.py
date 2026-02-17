# -*- coding: utf-8 -*-
from typing import List
from sentence_transformers import SentenceTransformer

from .config import EMBEDDING_MODEL

# Lazy inicializace modelu (načte se jen jednou)
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> List[float]:
    """
    Vrátí embedding jako seznam floatů.
    Pokud je text prázdný, vrací prázdný seznam.
    """
    if not text or not text.strip():
        return []
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()
