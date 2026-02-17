# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Optional

import chromadb
from chromadb.config import Settings

from app.modules.ai.rag.config import CHROMA_PATH
from app.modules.ai.rag.embeddings import embed_text


_client = None
_collection = None
COLLECTION_NAME = "product_templates"


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


def get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def add_template(doc_id: str, text: str, metadata: dict[str, Any]) -> None:
    embedding = embed_text(text)
    col = get_collection()
    col.add(
        ids=[doc_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def upsert_template(doc_id: str, text: str, metadata: dict[str, Any]) -> None:
    embedding = embed_text(text)
    col = get_collection()
    col.upsert(
        ids=[doc_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def list_templates() -> list[dict[str, Any]]:
    col = get_collection()
    result = col.get(include=["metadatas", "documents"])
    ids = result.get("ids") or []
    metas = result.get("metadatas") or []
    docs = result.get("documents") or []
    items: list[dict[str, Any]] = []
    for idx, doc_id in enumerate(ids):
        meta = metas[idx] if idx < len(metas) else {}
        if isinstance(meta, dict) and meta.get("system_rule"):
            continue
        doc = docs[idx] if idx < len(docs) else None
        items.append(
            {
                "id": doc_id,
                "title": meta.get("title") if isinstance(meta, dict) else None,
                "product_type": meta.get("product_type") if isinstance(meta, dict) else None,
                "price_czk": meta.get("price_czk") if isinstance(meta, dict) else None,
                "product_id": meta.get("product_id") if isinstance(meta, dict) else None,
                "created_at": meta.get("created_at") if isinstance(meta, dict) else None,
                "document": doc,
            }
        )
    return items


def search_templates(
    query_text: str,
    *,
    product_type: Optional[str] = None,
    n_results: int = 1,
):
    embedding = embed_text(query_text)
    if not embedding:
        return None
    col = get_collection()
    where = {"product_type": product_type} if product_type else None
    return col.query(
        query_embeddings=[embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
