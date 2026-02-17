# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from .config import CHROMA_PATH, CHROMA_COLLECTION
from .embeddings import embed_text
from .models.templates_model import TemplateExample


# Lazy inicializace klienta a kolekce
_client = None
_collection = None


def _get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.Client(
            Settings(
                persist_directory=CHROMA_PATH,
                is_persistent=True,
            )
        )
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION
        )
    return _collection


# ✅ NOVÁ VEŘEJNÁ FUNKCE — JEDINÁ ZMĚNA
def get_collection():
    return _get_collection()


def add_document(
    doc_id: str,
    text: str,
    embedding: List[float],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Přidá dokument do Chroma kolekce."""
    col = _get_collection()
    col.add(
        ids=[doc_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata or {}],
    )
    # persist() není potřeba — Chroma ukládá automaticky


def search(
    query_embedding: List[float],
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
):
    """Vyhledá v Chroma podle embeddingu."""
    col = _get_collection()
    return col.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )


def add_template_to_chroma(template: TemplateExample) -> None:
    """
    Uloží šablonu z adminu do Chroma jako RAG vzor.
    """
    text = f"{template.title_template}\n{template.description_template}"

    embedding = embed_text(text)

    metadata = {
        "product_type": template.product_type,
        "style": template.style,
        "tone": template.tone,
    }

    add_document(
        doc_id=str(template.id),
        text=text,
        embedding=embedding,
        metadata=metadata,
    )


def search_templates_by_product(
    query_text: str,
    product_type: str,
    n_results: int = 5,
):
    query_embedding = embed_text(query_text)

    return search(
        query_embedding=query_embedding,
        n_results=n_results,
        where={"product_type": product_type},
    )


def get_template_by_id(doc_id: str) -> Optional[str]:
    """
    Vrátí text šablony přímo podle doc_id (např. template_bracelet).
    """
    col = _get_collection()
    try:
        result = col.get(ids=[doc_id], include=["documents"])
        docs = result.get("documents") if result else None
        if docs and len(docs) > 0 and docs[0] and len(docs[0]) > 0:
            return docs[0][0]
    except Exception:
        pass
    return None
