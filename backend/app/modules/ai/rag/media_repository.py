# -*- coding: utf-8 -*-
from typing import List, Union
import os
import uuid
from pathlib import Path

from .models.media import MediaAsset

try:
    from app.db.session import get_db
    from app.db.models.product import Product
    from app.db.models.product_variant import ProductVariant
    HAS_DB = True
except Exception:
    HAS_DB = False
    Product = None
    ProductVariant = None


# Jednotná cesta: backend/static/uploads (žádné backend/app/static)
# media_repository.py je v backend/app/modules/ai/rag/ -> 4 úrovně nahoru = backend
_rag_dir = Path(__file__).resolve().parent
_backend_root = _rag_dir.parent.parent.parent.parent
UPLOAD_ROOT = (_backend_root / "static" / "uploads").as_posix()


def _filename_to_asset(filename: str, session_id: Union[int, str]) -> MediaAsset:
    """Sestaví jeden MediaAsset z názvu souboru (hlavní obrázek produktu nebo varianty)."""
    fn = (filename or "").strip()
    fn = os.path.basename(fn) if fn else ""
    full_path = os.path.join(UPLOAD_ROOT, fn) if fn else ""
    return MediaAsset(
        id=uuid.uuid4(),
        session_id=str(session_id),
        path_original=full_path,
        path_webp=None,
        width=None,
        height=None,
        vision_json=None,
        tags=[],
        embedding_hash=None,
    )


def get_media_assets_by_session(session_id: Union[int, str]) -> List[MediaAsset]:
    """
    Pro daný product_id (session_id) vrací pouze HLAVNÍ obrázek produktu (Product.image).
    Galerie (ProductMedia) se do Vision neposílá.
    """
    if not HAS_DB or Product is None:
        return []

    db = next(get_db())
    try:
        sid = int(session_id) if session_id is not None else 0
        product = db.query(Product).filter(Product.id == sid).first()
        if not product or not product.image:
            return []
        asset = _filename_to_asset(product.image, session_id)
        if asset.path_original and os.path.exists(asset.path_original):
            return [asset]
        return []
    finally:
        db.close()


def get_media_assets_for_variant(variant_id: Union[int, str]) -> List[MediaAsset]:
    """
    Pro danou variantu (variant_id) vrací pouze HLAVNÍ obrázek varianty (ProductVariant.image).
    Galerie varianty (ProductVariantMedia) se do Vision neposílá.
    """
    if not HAS_DB or ProductVariant is None:
        return []

    db = next(get_db())
    try:
        vid = int(variant_id) if variant_id is not None else 0
        variant = db.query(ProductVariant).filter(ProductVariant.id == vid).first()
        if not variant or not variant.image:
            return []
        asset = _filename_to_asset(variant.image, variant_id)
        if asset.path_original and os.path.exists(asset.path_original):
            return [asset]
        return []
    finally:
        db.close()
