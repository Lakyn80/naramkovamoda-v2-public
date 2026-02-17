from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .seed_templates import seed_rag_templates_from_db
from .service import generate_drafts_for_session
from .chroma_client import add_document, search
from .embeddings import embed_text
from app.modules.auth.deps import require_admin, require_admin_or_rag_seed

router = APIRouter(prefix="/api/ai/rag", tags=["ai-rag"])


class RagIngestRequest(BaseModel):
    category: str
    attributes: dict[str, list[str]]
    description: str


class RagSearchRequest(BaseModel):
    category: str
    attributes: dict[str, list[str]]


@router.post("/seed-templates")
def api_seed_rag_templates(_user=Depends(require_admin_or_rag_seed)):
    """
    Načte z DB jeden reálný produkt pro každou kategorii (bracelet, candle, necklace, earrings, decor, other)
    a uloží ho jako šablonu do Chroma (template_<kategorie>).
    RAG určuje styl a strukturu, obsah vždy z Vision.
    """
    outcomes = seed_rag_templates_from_db()
    return {"status": "ok", "outcomes": outcomes}


@router.get("/drafts/{product_id}")
def api_get_draft(product_id: int, _user=Depends(require_admin)):
    """
    Vygeneruje draft (název + popis) pro produkt podle obrázků: Vision → RAG šablona → LLM.
    product_id = ID produktu v DB (musí mít záznamy v product_media a soubory v backend/static/uploads).
    """
    try:
        draft = generate_drafts_for_session(product_id)
        return draft
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_rag_text(attributes: dict[str, list[str]], description: str | None) -> str:
    labels = attributes.get("labels") or []
    colors = attributes.get("colors") or []
    objects = attributes.get("objects") or []
    parts = [
        f"labels: {', '.join(labels)}" if labels else "",
        f"colors: {', '.join(colors)}" if colors else "",
        f"objects: {', '.join(objects)}" if objects else "",
        description or "",
    ]
    return "\n".join([p for p in parts if p]).strip()


@router.post("/ingest")
def ingest_rag(payload: RagIngestRequest, _user=Depends(require_admin)) -> dict[str, Any]:
    text = _build_rag_text(payload.attributes or {}, payload.description)
    if not text:
        raise HTTPException(status_code=400, detail="Nothing to ingest")
    embedding = embed_text(text)
    doc_id = f"rag_{uuid.uuid4().hex}"
    add_document(
        doc_id=doc_id,
        text=text,
        embedding=embedding,
        metadata={"category": payload.category},
    )
    return {"status": "ok", "id": doc_id}


@router.post("/search")
def search_rag(payload: RagSearchRequest, _user=Depends(require_admin)) -> dict[str, Any]:
    text = _build_rag_text(payload.attributes or {}, None)
    if not text:
        raise HTTPException(status_code=400, detail="Nothing to search")
    embedding = embed_text(text)
    result = search(query_embedding=embedding, n_results=5, where={"category": payload.category})
    return result or {}
