from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.paths import UPLOAD_DIR
from app.db.models import (
    MediaInboxItem,
    MediaSecondInboxItem,
    Product,
    ProductMedia,
    ProductVariant,
    ProductVariantMedia,
)
from app.db.session import get_db
from app.modules.auth.deps import require_admin
from app.modules.media_inbox.ai_draft_service import generate_draft_for_inbox_image
from .inbox_repository import add_inbox_item, get_pending_items
from .webp_converter import convert_to_webp

router = APIRouter(prefix="/api/media-second", tags=["media-second-inbox"], dependencies=[Depends(require_admin)])
logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("NMM_AI_BATCH_SIZE", "3") or "3")
BATCH_PAUSE_SEC = float(os.getenv("NMM_AI_BATCH_PAUSE_SEC", "0.8") or "0.8")

class AssignSecondInboxItem(BaseModel):
    second_inbox_id: int
    assign_to_product: int | None = None
    assign_to_variant: int | None = None


class AssignSecondInboxRequest(BaseModel):
    items: list[AssignSecondInboxItem]


class DeleteBatchRequest(BaseModel):
    ids: list[int]


class MoveBatchRequest(BaseModel):
    ids: list[int]


def _save_upload_to_temp(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            tmp.write(chunk)
        return tmp.name


def _relative_upload_path(abs_path: str) -> str:
    p = Path(abs_path)
    try:
        rel = p.relative_to(UPLOAD_DIR)
        return rel.as_posix()
    except Exception:
        return p.name


def _abs_upload_path(webp_path: str) -> Path:
    rel = webp_path.replace("\\", "/")
    if rel.startswith("/static/uploads/"):
        rel = rel[len("/static/uploads/") :]
    if rel.startswith("static/uploads/"):
        rel = rel[len("static/uploads/") :]
    rel = rel.lstrip("/")
    return UPLOAD_DIR / rel


def _candidate_paths(webp_path: str) -> list[str]:
    if not webp_path:
        return []
    normalized = webp_path.lstrip("/")
    candidates = {
        webp_path,
        normalized,
        f"/static/uploads/{normalized}",
        f"static/uploads/{normalized}",
        Path(webp_path).name,
    }
    return [c for c in candidates if c]


def _is_file_referenced(db: Session, webp_path: str) -> bool:
    candidates = _candidate_paths(webp_path)
    if not candidates:
        return False
    return any(
        [
            db.query(Product.id).filter(or_(*[Product.image == c for c in candidates])).first(),
            db.query(ProductVariant.id)
            .filter(or_(*[ProductVariant.image == c for c in candidates]))
            .first(),
            db.query(ProductMedia.id)
            .filter(or_(*[ProductMedia.filename == c for c in candidates]))
            .first(),
            db.query(ProductVariantMedia.id)
            .filter(or_(*[ProductVariantMedia.filename == c for c in candidates]))
            .first(),
            db.query(MediaInboxItem.id)
            .filter(or_(*[MediaInboxItem.webp_path == c for c in candidates]))
            .first(),
            db.query(MediaSecondInboxItem.id)
            .filter(or_(*[MediaSecondInboxItem.webp_path == c for c in candidates]))
            .first(),
        ]
    )


def _delete_upload_file_if_unreferenced(db: Session, webp_path: str) -> None:
    if not webp_path:
        return
    if _is_file_referenced(db, webp_path):
        return
    path = _abs_upload_path(webp_path)
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _resolve_existing_upload_path(webp_path: str) -> Path | None:
    for cand in _candidate_paths(webp_path):
        rel = cand.replace("\\", "/")
        if rel.startswith("/static/uploads/"):
            rel = rel[len("/static/uploads/") :]
        if rel.startswith("static/uploads/"):
            rel = rel[len("static/uploads/") :]
        rel = rel.lstrip("/")
        abs_path = UPLOAD_DIR / rel
        if abs_path.exists():
            return abs_path
    abs_path = Path(webp_path)
    if abs_path.is_absolute() and abs_path.exists():
        return abs_path
    return None


def _move_upload_file(src_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src_path.name
    if dest_path.exists():
        dest_path = dest_dir / f"{uuid.uuid4().hex}{src_path.suffix}"
    src_path.replace(dest_path)
    return dest_path


def _copy_upload_file(src_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src_path.name
    if dest_path.exists():
        dest_path = dest_dir / f"{uuid.uuid4().hex}{src_path.suffix}"
    shutil.copy2(src_path, dest_path)
    return dest_path


def _persist_assigned_media(webp_path: str, *, dest_subdir: str = "catalog_webp") -> str:
    """Copy assigned inbox media into stable catalog storage."""
    src_path = _resolve_existing_upload_path(webp_path)
    if not src_path:
        return webp_path

    try:
        rel_src = src_path.relative_to(UPLOAD_DIR).as_posix()
        if rel_src.startswith(f"{dest_subdir}/"):
            return rel_src
    except Exception:
        pass

    dest_path = _copy_upload_file(src_path, UPLOAD_DIR / dest_subdir)
    return _relative_upload_path(str(dest_path))


def _iter_batches(items: list[Any], size: int) -> list[list[Any]]:
    batch_size = max(int(size), 1)
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


@router.post("/upload")
async def upload_media_second_inbox(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    imported = 0

    for upload in files:
        if not upload or not upload.filename:
            continue
        temp_path = _save_upload_to_temp(upload)
        try:
            webp_abs_path = convert_to_webp(temp_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"{upload.filename}: {exc}") from exc
        webp_rel = _relative_upload_path(webp_abs_path)

        add_inbox_item(db, webp_path=webp_rel, filename=upload.filename or None)
        imported += 1

    pending_count = len(get_pending_items(db))
    return {"imported": imported, "pending_items": pending_count}


@router.get("/pending")
async def list_pending_media_second_inbox(db: Session = Depends(get_db)) -> dict[str, Any]:
    items = get_pending_items(db)
    return {
        "items": [
            {
                "id": i.id,
                "filename": i.filename,
                "webp_path": i.webp_path,
                "product_type": i.product_type,
                "status": i.status,
            }
            for i in items
            if i is not None and i.id is not None
        ]
    }


@router.post("/delete-batch")
async def delete_media_second_batch(
    payload: DeleteBatchRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    deleted: list[int] = []
    errors: list[dict[str, Any]] = []
    file_paths: list[str] = []

    for item_id in payload.ids:
        item = db.get(MediaSecondInboxItem, item_id)
        if not item:
            errors.append({"id": item_id, "error": "not found"})
            continue
        file_paths.append(item.webp_path)
        db.delete(item)
        deleted.append(item_id)

    db.commit()

    for path in file_paths:
        _delete_upload_file_if_unreferenced(db, path)

    return {"deleted": deleted, "errors": errors}


@router.delete("/all")
async def delete_media_second_all(db: Session = Depends(get_db)) -> dict[str, Any]:
    items = db.query(MediaSecondInboxItem).all()
    file_paths = [item.webp_path for item in items if item.webp_path]

    db.query(MediaSecondInboxItem).delete(synchronize_session=False)
    db.commit()

    for path in file_paths:
        _delete_upload_file_if_unreferenced(db, path)

    inbox_dir = UPLOAD_DIR / "second_inbox_webp"
    if inbox_dir.exists():
        for path in inbox_dir.rglob("*"):
            if path.is_file():
                rel_path = _relative_upload_path(str(path))
                _delete_upload_file_if_unreferenced(db, rel_path)

    return {"deleted": len(items)}


@router.delete("/{item_id}")
async def delete_media_second_item(item_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(MediaSecondInboxItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    webp_path = item.webp_path
    db.delete(item)
    db.commit()
    _delete_upload_file_if_unreferenced(db, webp_path)
    return {"deleted_id": item_id}


@router.post("/move-to-ai")
async def move_media_second_to_ai(
    payload: MoveBatchRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    moved: list[dict[str, int]] = []
    errors: list[dict[str, Any]] = []

    batches = _iter_batches(list(payload.ids or []), BATCH_SIZE)
    for idx, batch in enumerate(batches):
        for item_id in batch:
            src_path: Path | None = None
            dest_path: Path | None = None
            try:
                with db.begin_nested():
                    item = db.get(MediaSecondInboxItem, item_id)
                    if not item:
                        raise ValueError("not found")
                    if item.status != "pending":
                        raise ValueError("item is not pending")

                    src_path = _resolve_existing_upload_path(item.webp_path)
                    if not src_path:
                        raise ValueError("file not found on disk")

                    dest_path = _move_upload_file(src_path, UPLOAD_DIR / "inbox_webp")
                    new_rel = _relative_upload_path(str(dest_path))

                    draft = generate_draft_for_inbox_image(str(dest_path))
                    inbox_item = MediaInboxItem(
                        filename=item.filename,
                        webp_path=new_rel,
                        draft_title=draft.get("title"),
                        draft_description=draft.get("description"),
                        product_type=draft.get("product_type"),
                        combined_tags=draft.get("combined_tags"),
                        status="pending",
                    )
                    db.add(inbox_item)
                    db.flush()
                    db.delete(item)
                    moved.append({"from": item_id, "to": inbox_item.id})
            except Exception as exc:
                if dest_path and src_path and dest_path.exists() and not src_path.exists():
                    try:
                        dest_path.replace(src_path)
                    except Exception:
                        pass
                errors.append({"id": item_id, "error": str(exc)})
                continue
        if idx < len(batches) - 1 and BATCH_PAUSE_SEC > 0:
            await asyncio.sleep(BATCH_PAUSE_SEC)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    if errors:
        logger.warning("media-second move-to-ai errors: %s", errors)

    return {"moved": moved, "errors": errors}


@router.post("/assign")
async def assign_media_second_inbox(
    payload: AssignSecondInboxRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        if not payload.items:
            raise HTTPException(status_code=400, detail="items must not be empty")

        assigned_products: list[int] = []
        assigned_variants: list[int] = []
        errors: list[dict[str, Any]] = []

        for item in payload.items:
            try:
                with db.begin_nested():
                    inbox_item = db.get(MediaSecondInboxItem, item.second_inbox_id)
                    if not inbox_item:
                        raise ValueError(f"Second inbox item {item.second_inbox_id} not found")

                    if item.assign_to_product and item.assign_to_variant:
                        raise ValueError(
                            f"Provide assign_to_product or assign_to_variant for {item.second_inbox_id}"
                        )

                    if item.assign_to_product:
                        product = db.get(Product, item.assign_to_product)
                        if not product:
                            raise ValueError(f"Product {item.assign_to_product} not found")

                        assigned_path = _persist_assigned_media(inbox_item.webp_path)
                        db.add(
                            ProductMedia(
                                product_id=product.id,
                                filename=assigned_path,
                                media_type="image",
                            )
                        )
                        inbox_item.status = "assigned"
                        assigned_products.append(product.id)
                        continue

                    if item.assign_to_variant:
                        variant = db.get(ProductVariant, item.assign_to_variant)
                        if not variant:
                            raise ValueError(f"Variant {item.assign_to_variant} not found")

                        assigned_path = _persist_assigned_media(inbox_item.webp_path)
                        db.add(
                            ProductVariantMedia(
                                variant_id=variant.id,
                                filename=assigned_path,
                            )
                        )
                        inbox_item.status = "assigned"
                        assigned_variants.append(variant.id)
                        continue

                    raise ValueError(
                        f"assign_to_product or assign_to_variant is required for {item.second_inbox_id}"
                    )
            except Exception as exc:
                errors.append({"second_inbox_id": item.second_inbox_id, "error": str(exc)})
                continue

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(exc))

        return {
            "assigned": len(assigned_products) + len(assigned_variants),
            "product_ids": assigned_products,
            "variant_ids": assigned_variants,
            "errors": errors,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
