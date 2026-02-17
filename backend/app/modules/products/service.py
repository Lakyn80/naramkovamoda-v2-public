from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.pricing_rules import infer_bracelet_price_czk
from app.core.paths import UPLOAD_DIR
from app.db.models import (
    Category,
    MediaInboxItem,
    MediaSecondInboxItem,
    Product,
    ProductMedia,
    ProductVariant,
    ProductVariantMedia,
)

MAIN_IMAGE_ORIGINAL_MEDIA_TYPE = "main_original"
MAIN_IMAGE_FULL_MEDIA_TYPE = "main_full"
MAIN_IMAGE_THUMB_MEDIA_TYPE = "main_thumb"
MAIN_IMAGE_MEDIA_TYPES = {
    MAIN_IMAGE_ORIGINAL_MEDIA_TYPE,
    MAIN_IMAGE_FULL_MEDIA_TYPE,
    MAIN_IMAGE_THUMB_MEDIA_TYPE,
}
MAIN_IMAGE_FULL_MAX_WIDTH = 1400
MAIN_IMAGE_THUMB_MAX_WIDTH = 600
MAIN_IMAGE_FULL_QUALITY = 82
MAIN_IMAGE_THUMB_QUALITY = 75
PROTECTED_UPLOAD_PREFIXES = ("inbox_webp/", "second_inbox_webp/")


def _ensure_uploads_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def _safe_uuid_name(filename: str | None) -> str:
    ext = ""
    if filename:
        _, ext = os.path.splitext(filename)
    if not ext:
        ext = ".bin"
    return f"{uuid.uuid4().hex}{ext.lower()}"


def _normalize_upload_filename(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).replace("\\", "/").strip()
    if "/static/uploads/" in v:
        v = v.split("/static/uploads/")[-1]
    if "static/uploads/" in v:
        v = v.split("static/uploads/")[-1]
    v = v.lstrip("/")
    while v.startswith("uploads/"):
        v = v[len("uploads/"):]
    return v or None


def _ensure_webp_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    lower = filename.lower()
    if lower.endswith(".webp"):
        return filename
    base, ext = os.path.splitext(filename)
    if not base:
        return None
    src_path = UPLOAD_DIR / filename
    webp_name = f"{base}.webp"
    webp_path = UPLOAD_DIR / webp_name
    if webp_path.exists():
        return webp_name
    if not src_path.exists():
        return None

    try:
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)

            if img.mode in ("I;16", "I", "F"):
                img = img.convert("RGB")
            elif img.mode in ("P", "LA"):
                img = img.convert("RGBA")
            elif img.mode == "CMYK":
                img = img.convert("RGB")

            save_kwargs: dict[str, Any] = {
                "format": "WEBP",
                "method": 6,
                "optimize": True,
            }
            icc = img.info.get("icc_profile")
            if icc:
                save_kwargs["icc_profile"] = icc
            try:
                exif = img.getexif()
                if exif:
                    save_kwargs["exif"] = exif.tobytes()
            except Exception:
                pass

            ext = ext.lower()
            if ext in (".jpg", ".jpeg", ".heic", ".heif"):
                save_kwargs["lossless"] = False
                save_kwargs["quality"] = 72
            elif ext == ".png":
                if img.mode in ("RGBA", "LA"):
                    save_kwargs["lossless"] = True
                else:
                    save_kwargs["lossless"] = True
                    save_kwargs["quality"] = 90
            else:
                save_kwargs["lossless"] = False
                save_kwargs["quality"] = 72

            img.save(webp_path, **save_kwargs)
        return webp_name
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _save_upload_file(upload: UploadFile) -> str:
    _ensure_uploads_dir()
    filename = _safe_uuid_name(upload.filename)
    target = UPLOAD_DIR / filename
    with target.open("wb") as f:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            f.write(chunk)
    return filename


def _main_media_type(kind: str | None) -> str | None:
    if kind == "original":
        return MAIN_IMAGE_ORIGINAL_MEDIA_TYPE
    if kind == "full":
        return MAIN_IMAGE_FULL_MEDIA_TYPE
    if kind == "thumb":
        return MAIN_IMAGE_THUMB_MEDIA_TYPE
    return None


def _is_main_media_row(media: ProductMedia) -> bool:
    return (media.media_type or "").strip().lower() in MAIN_IMAGE_MEDIA_TYPES


def _render_variant_webp(
    source_filename: str | None,
    *,
    suffix: str,
    max_width: int,
    quality: int,
) -> str | None:
    src_name = _normalize_upload_filename(source_filename)
    if not src_name:
        return None
    src_path = UPLOAD_DIR / src_name
    if not src_path.exists():
        return None

    base, _ = os.path.splitext(src_name)
    if not base:
        return None
    out_name = f"{base}_{suffix}.webp"
    out_path = UPLOAD_DIR / out_name

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src_path) as img:
            img = ImageOps.exif_transpose(img)

            if max_width and img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = max(1, int(round(img.height * ratio)))
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            if img.mode in ("I;16", "I", "F"):
                img = img.convert("RGB")
            elif img.mode in ("P", "LA"):
                img = img.convert("RGBA")
            elif img.mode == "CMYK":
                img = img.convert("RGB")

            save_kwargs: dict[str, Any] = {
                "format": "WEBP",
                "method": 6,
                "optimize": True,
                "lossless": False,
                "quality": int(quality),
            }
            icc = img.info.get("icc_profile")
            if icc:
                save_kwargs["icc_profile"] = icc
            try:
                exif = img.getexif()
                if exif:
                    save_kwargs["exif"] = exif.tobytes()
            except Exception:
                pass

            img.save(out_path, **save_kwargs)
        return out_name
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def _save_main_image_assets(upload: UploadFile) -> dict[str, str]:
    original = _save_upload_file(upload)
    full = _render_variant_webp(
        original,
        suffix="full",
        max_width=MAIN_IMAGE_FULL_MAX_WIDTH,
        quality=MAIN_IMAGE_FULL_QUALITY,
    )
    thumb = _render_variant_webp(
        original,
        suffix="thumb",
        max_width=MAIN_IMAGE_THUMB_MAX_WIDTH,
        quality=MAIN_IMAGE_THUMB_QUALITY,
    )

    fallback_webp = _ensure_webp_filename(original)
    full = full or fallback_webp or original
    thumb = thumb or full
    return {
        "original": original,
        "full": full,
        "thumb": thumb,
    }


def _collect_main_image_files(product: Product) -> set[str]:
    files: set[str] = set()
    if product.image:
        files.add(product.image)
    for media in list(product.media or []):
        if _is_main_media_row(media) and media.filename:
            files.add(media.filename)
    return files


def _replace_main_media_rows(
    db: Session,
    *,
    product_id: int,
    assets: dict[str, str] | None,
) -> None:
    (
        db.query(ProductMedia)
        .filter(
            ProductMedia.product_id == product_id,
            ProductMedia.media_type.in_(tuple(MAIN_IMAGE_MEDIA_TYPES)),
        )
        .delete(synchronize_session=False)
    )
    if not assets:
        return

    for kind in ("original", "full", "thumb"):
        filename = _normalize_upload_filename(assets.get(kind))
        media_type = _main_media_type(kind)
        if not filename or not media_type:
            continue
        _ensure_product_media_row(
            db,
            product_id=product_id,
            filename=filename,
            media_type=media_type,
        )


def _public_media_url(filename: str | None, media_type: str | None = None) -> str | None:
    normalized = _normalize_upload_filename(filename)
    if not normalized:
        return None

    mt = (media_type or "").strip().lower()
    if mt == "video":
        return f"/static/uploads/{normalized}"

    webp_name = _ensure_webp_filename(normalized)
    if webp_name:
        return f"/static/uploads/{webp_name}"

    if (UPLOAD_DIR / normalized).exists():
        return f"/static/uploads/{normalized}"
    return None


def _resolve_main_image_filenames(product: Product) -> tuple[str | None, str | None]:
    full_name = _normalize_upload_filename(product.image)
    thumb_name: str | None = None

    for media in list(product.media or []):
        if not media.filename:
            continue
        mt = (media.media_type or "").strip().lower()
        if mt == MAIN_IMAGE_FULL_MEDIA_TYPE:
            full_name = _normalize_upload_filename(media.filename) or full_name
        elif mt == MAIN_IMAGE_THUMB_MEDIA_TYPE:
            thumb_name = _normalize_upload_filename(media.filename) or thumb_name
        elif mt == MAIN_IMAGE_ORIGINAL_MEDIA_TYPE and not full_name:
            full_name = _normalize_upload_filename(media.filename) or full_name

    return full_name, thumb_name


def _split_image_suffix(filename: str | None) -> tuple[str | None, str | None]:
    normalized = _normalize_upload_filename(filename)
    if not normalized:
        return None, None

    path = Path(normalized)
    stem = path.stem
    suffix: str | None = None
    if stem.endswith("_full"):
        stem = stem[:-5]
        suffix = "full"
    elif stem.endswith("_thumb"):
        stem = stem[:-6]
        suffix = "thumb"

    base = (path.parent / stem) if str(path.parent) not in ("", ".") else Path(stem)
    return base.as_posix(), suffix


def _variant_related_files(filename: str | None) -> set[str]:
    normalized = _normalize_upload_filename(filename)
    if not normalized:
        return set()

    result: set[str] = {normalized}
    base_key, _ = _split_image_suffix(normalized)
    if not base_key:
        return result

    full_candidate = f"{base_key}_full.webp"
    thumb_candidate = f"{base_key}_thumb.webp"
    for candidate in (full_candidate, thumb_candidate):
        if (UPLOAD_DIR / candidate).exists():
            result.add(candidate)

    base_path = Path(base_key)
    base_dir = (UPLOAD_DIR / base_path.parent) if str(base_path.parent) not in ("", ".") else UPLOAD_DIR
    pattern = f"{base_path.name}.*"
    if base_dir.exists():
        for file_path in base_dir.glob(pattern):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(UPLOAD_DIR).as_posix()
            if rel.endswith("_full.webp") or rel.endswith("_thumb.webp"):
                continue
            result.add(rel)

    return result


def _resolve_variant_image_filenames(filename: str | None) -> tuple[str | None, str | None]:
    normalized = _normalize_upload_filename(filename)
    if not normalized:
        return None, None

    base_key, suffix = _split_image_suffix(normalized)
    full_candidate = f"{base_key}_full.webp" if base_key else None
    thumb_candidate = f"{base_key}_thumb.webp" if base_key else None

    def exists(name: str | None) -> bool:
        return bool(name and (UPLOAD_DIR / name).exists())

    full_name: str | None = None
    thumb_name: str | None = None

    if suffix == "full":
        full_name = normalized
        thumb_name = thumb_candidate if exists(thumb_candidate) else normalized
    elif suffix == "thumb":
        thumb_name = normalized
        full_name = full_candidate if exists(full_candidate) else normalized
    else:
        if exists(full_candidate):
            full_name = full_candidate
        elif exists(normalized):
            full_name = normalized
        else:
            full_name = _ensure_webp_filename(normalized) or normalized
        if exists(thumb_candidate):
            thumb_name = thumb_candidate
        else:
            thumb_name = full_name

    return full_name, thumb_name


def _detect_media_type(filename: str | None, mimetype: str | None) -> str:
    mt = (mimetype or "").lower()
    if mt.startswith("video/"):
        return "video"
    if mt.startswith("image/"):
        return "image"
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        return "video"
    return "image"


def _ensure_product_media_row(
    db: Session,
    *,
    product_id: int,
    filename: str | None,
    media_type: str | None,
) -> None:
    if not filename:
        return
    mt = (media_type or "image").strip() or "image"
    exists = (
        db.query(ProductMedia)
        .filter_by(product_id=product_id, filename=filename)
        .first()
    )
    if not exists:
        db.add(ProductMedia(product_id=product_id, filename=filename, media_type=mt))


def _delete_product_media_row(db: Session, *, product_id: int, filename: str | None) -> None:
    if not filename:
        return
    (
        db.query(ProductMedia)
        .filter_by(product_id=product_id, filename=filename)
        .delete(synchronize_session=False)
    )


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _to_int(val, default=None):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _to_price(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _category_context(db: Session, category_id: int | None) -> tuple[str | None, str | None]:
    if category_id is None:
        return None, None
    category = db.get(Category, category_id)
    if not category:
        return None, None
    return getattr(category, "name", None), getattr(category, "slug", None)


def _auto_product_price(
    *,
    category_name: str | None,
    category_slug: str | None,
    name: str | None,
    description: str | None,
) -> float | None:
    return infer_bracelet_price_czk(
        category_name=category_name,
        category_slug=category_slug,
        title=name,
        description=description,
        tags=None,
    )


def _auto_variant_price(
    *,
    category_name: str | None,
    category_slug: str | None,
    product_name: str | None,
    product_description: str | None,
    variant_name: str | None,
    variant_description: str | None,
) -> float | None:
    return infer_bracelet_price_czk(
        category_name=category_name,
        category_slug=category_slug,
        title=variant_name or product_name,
        description=variant_description or product_description,
        tags=None,
    )


def _to_bool(val, default=None):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


def _parse_variants_from_form(
    form: dict[str, Any],
    files: dict[str, list[UploadFile]],
    *,
    is_add_request: bool,
) -> tuple[list[dict[str, Any]], bool]:
    variants: list[dict[str, Any]] = []
    explicit = False

    raw_form_variants = form.get("variants")
    if raw_form_variants is not None:
        try:
            parsed = json.loads(raw_form_variants) or []
            if isinstance(parsed, list):
                explicit = True
                for v in parsed:
                    if not isinstance(v, dict):
                        continue
                    variants.append(
                        {
                            "id": _to_int(v.get("id"), default=None),
                            "variant_name": (v.get("variant_name") or v.get("name") or "").strip() or None,
                            "wrist_size": (v.get("wrist_size") or "").strip() or None,
                            "description": (v.get("description") or "").strip() or None,
                            "price_czk": _to_price(v.get("price_czk") or v.get("price")),
                            "stock": _to_int(v.get("stock"), default=None),
                            "image": (v.get("image") or "").strip() or None,
                        }
                    )
        except Exception:
            pass

    names = _listify(form.get("variant_name[]"))
    wrists = _listify(form.get("variant_wrist_size[]"))
    stocks = _listify(form.get("variant_stock[]"))
    descriptions = _listify(form.get("variant_description[]"))
    prices = _listify(form.get("variant_price[]"))
    ids = _listify(form.get("variant_id[]"))
    main_files = _listify(files.get("variant_image[]"))

    if any([names, wrists, stocks, descriptions, prices, main_files]):
        explicit = True

    max_len = max(len(names), len(wrists), len(stocks), len(descriptions), len(prices), len(ids))
    if max_len == 0 and main_files:
        max_len = len(main_files)

    existing_main = [] if is_add_request else _listify(form.get("variant_image_existing[]"))

    for i in range(max_len):
        n = names[i] if i < len(names) else ""
        w = wrists[i] if i < len(wrists) else ""
        s_raw = stocks[i] if i < len(stocks) else None
        s_val = _to_int(s_raw, default=None)
        desc = descriptions[i] if i < len(descriptions) else None
        price_val = prices[i] if i < len(prices) else None
        f = main_files[i] if i < len(main_files) else None
        has_file = bool(f and getattr(f, "filename", None))
        existing = existing_main[i] if i < len(existing_main) else None

        extra_files = _listify(files.get(f"variant_image_multi_{i}[]"))
        extra_existing = [] if is_add_request else _listify(form.get(f"variant_image_existing_multi_{i}[]"))

        if not (n or w or has_file or existing or price_val):
            continue

        variants.append(
            {
                "id": _to_int(ids[i] if i < len(ids) else None, default=None),
                "variant_name": (n or None),
                "wrist_size": (w or None),
                "description": (desc or None),
                "price_czk": _to_price(price_val),
                "stock": s_val,
                "image_file": f if has_file else None,
                "existing_image": None if is_add_request else (existing or None),
                "extra_files": [ef for ef in extra_files if getattr(ef, "filename", None)],
                "existing_extra": [] if is_add_request else [ee for ee in extra_existing if ee],
            }
        )

    return variants, explicit


def _parse_variants_from_json(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    variants: list[dict[str, Any]] = []
    explicit = False

    # Variants are explicit only when the request actually includes "variants".
    # Missing key means "do not touch existing variants".
    has_variants_key = isinstance(payload, dict) and "variants" in payload
    raw_list = payload.get("variants") if has_variants_key else None
    if isinstance(raw_list, list):
        explicit = True
        for v in raw_list:
            if not isinstance(v, dict):
                continue
            variants.append(
                {
                    "id": _to_int(v.get("id"), default=None),
                    "variant_name": (v.get("variant_name") or v.get("name") or "").strip() or None,
                    "wrist_size": (v.get("wrist_size") or "").strip() or None,
                    "description": (v.get("description") or "").strip() or None,
                    "price_czk": _to_price(v.get("price_czk") or v.get("price")),
                    "stock": _to_int(v.get("stock"), default=None),
                    "image": (v.get("image") or "").strip() or None,
                }
            )

    return variants, explicit


def _dedupe_variants(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple] = set()
    result: list[dict[str, Any]] = []
    for v in items:
        key = (
            int(v.get("id")) if v.get("id") is not None else None,
            (v.get("variant_name") or "").strip().lower(),
            (v.get("wrist_size") or "").strip().lower(),
            (v.get("description") or "").strip().lower(),
            float(v["price_czk"]) if v.get("price_czk") is not None else None,
            int(v.get("stock")) if v.get("stock") is not None else None,
            (v.get("existing_image") or v.get("image") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(v)
    return result


def _variant_media_dict(media: ProductVariantMedia) -> dict[str, Any]:
    full_name, thumb_name = _resolve_variant_image_filenames(media.filename)
    image_full_url = _public_media_url(full_name, "image")
    image_thumb_url = _public_media_url(thumb_name, "image") or image_full_url
    return {
        "id": media.id,
        "image": media.filename,
        "image_url": image_full_url,
        "image_full_url": image_full_url,
        "image_thumb_url": image_thumb_url,
    }


def _variant_dict(variant: ProductVariant) -> dict[str, Any]:
    full_name, thumb_name = _resolve_variant_image_filenames(variant.image)
    image_full_url = _public_media_url(full_name, "image")
    image_thumb_url = _public_media_url(thumb_name, "image") or image_full_url
    return {
        "id": variant.id,
        "variant_name": variant.variant_name,
        "wrist_size": variant.wrist_size,
        "description": variant.description,
        "price_czk": float(variant.price_czk) if variant.price_czk is not None else None,
        "stock": variant.stock,
        "image": variant.image,
        "image_url": image_full_url,
        "image_full_url": image_full_url,
        "image_thumb_url": image_thumb_url,
        "media": [_variant_media_dict(m) for m in (variant.media or [])],
    }


def _product_dict(product: Product) -> dict[str, Any]:
    category_name = product.category.name if product.category else None
    category_group = product.category.group if product.category else None
    full_name, thumb_name = _resolve_main_image_filenames(product)
    image_full_url = _public_media_url(full_name, "image")
    image_thumb_url = _public_media_url(thumb_name, "image") or image_full_url

    media_urls: list[str] = []
    media_items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for media in list(product.media or []):
        if _is_main_media_row(media):
            continue
        url = _public_media_url(media.filename, media.media_type)
        if url and url not in seen_urls:
            seen_urls.add(url)
            media_urls.append(url)
        media_items.append(
            {
                "id": media.id,
                "filename": media.filename,
                "media_type": media.media_type,
                "url": url,
            }
        )

    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "seo_title": product.seo_title,
        "seo_description": product.seo_description,
        "seo_keywords": product.seo_keywords,
        "price": float(product.price_czk) if product.price_czk is not None else None,
        "stock": product.stock,
        "active": bool(getattr(product, "active", True)),
        "category_id": product.category_id,
        "category_name": category_name,
        "category_slug": getattr(product.category, "slug", None),
        "wrist_size": product.wrist_size,
        "image_url": image_full_url,
        "image_full_url": image_full_url,
        "image_thumb_url": image_thumb_url,
        "media": media_urls,
        "media_items": media_items,
        "categories": ([category_name] if category_name else []),
        "category_group": category_group,
        "variants": [_variant_dict(v) for v in (product.variants or [])],
    }


def list_products(db: Session, *, include_inactive: bool = False) -> list[dict[str, Any]]:
    q = (
        db.query(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.category),
            selectinload(Product.variants).selectinload(ProductVariant.media),
        )
    )
    if not include_inactive and hasattr(Product, "active"):
        q = q.filter(Product.active.is_(True))

    items = q.order_by(Product.id.desc()).all()
    return [_product_dict(p) for p in items]


def get_product(db: Session, product_id: int) -> dict[str, Any] | None:
    product = (
        db.query(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.category),
            selectinload(Product.variants).selectinload(ProductVariant.media),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        return None
    return _product_dict(product)


def create_product(
    db: Session,
    *,
    payload: dict[str, Any],
    form: dict[str, Any] | None,
    files: dict[str, list[UploadFile]] | None,
) -> dict[str, Any]:
    data = payload or {}
    form = form or {}
    files = files or {}

    name = (data.get("name") or form.get("name") or "").strip()
    description = (data.get("description") or form.get("description") or "").strip()
    seo_title = (data.get("seo_title") or form.get("seo_title") or "").strip()
    seo_description = (data.get("seo_description") or form.get("seo_description") or "").strip()
    seo_keywords = (data.get("seo_keywords") or form.get("seo_keywords") or "").strip()
    price_raw = str(
        data.get("price")
        or data.get("price_czk")
        or form.get("price")
        or form.get("price_czk")
        or ""
    ).strip()
    if "stock" in data:
        stock_raw_value = data.get("stock")
    elif "stock" in form:
        stock_raw_value = form.get("stock")
    else:
        stock_raw_value = None
    stock_raw = "" if stock_raw_value is None else str(stock_raw_value).strip()
    active_raw = data.get("active") if "active" in data else form.get("active")
    category_id = data.get("category_id") or form.get("category_id")
    wrist_size_raw = (
        data.get("wrist_size")
        or data.get("wrist_sizes")
        or form.get("wrist_size")
        or form.get("wrist_sizes")
        or ""
    ).strip()

    if not name or not category_id:
        raise ValueError("Missing required fields")

    try:
        category_id_int = int(category_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid category_id") from exc

    category_name, category_slug = _category_context(db, category_id_int)
    auto_price = _auto_product_price(
        category_name=category_name,
        category_slug=category_slug,
        name=name,
        description=description,
    )

    if not price_raw and auto_price is None:
        raise ValueError("Missing required fields")

    if price_raw:
        try:
            price = float(price_raw)
        except ValueError as exc:
            raise ValueError("Invalid price") from exc
    else:
        price = float(auto_price)

    try:
        stock = int(stock_raw) if stock_raw != "" else 1
        if stock < 0:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Invalid stock") from exc

    product = Product(
        name=name,
        description=(description or None),
        seo_title=(seo_title or None),
        seo_description=(seo_description or None),
        seo_keywords=(seo_keywords or None),
        price_czk=price,
        stock=stock,
        active=_to_bool(active_raw, default=True),
        category_id=category_id_int,
        wrist_size=wrist_size_raw or None,
    )
    if stock <= 0:
        product.active = False

    main_image_assets: dict[str, str] | None = None
    image_file = (files.get("image") or [None])[0]
    if image_file and image_file.filename:
        main_image_assets = _save_main_image_assets(image_file)
        product.image = main_image_assets.get("full")

    variants_payload, explicit_variants = _parse_variants_from_json(data)
    if form:
        form_variants, explicit_form = _parse_variants_from_form(form, files, is_add_request=True)
        if explicit_form:
            variants_payload = form_variants
            explicit_variants = True

    variants_payload = _dedupe_variants(variants_payload)

    try:
        db.add(product)
        db.flush()

        _replace_main_media_rows(
            db,
            product_id=product.id,
            assets=main_image_assets,
        )

        for variant in variants_payload:
            img_name = _normalize_upload_filename(variant.get("image") or None)
            if variant.get("image_file"):
                image_assets = _save_main_image_assets(variant["image_file"])
                img_name = _normalize_upload_filename(image_assets.get("full")) or img_name

            if not (
                variant.get("variant_name")
                or variant.get("wrist_size")
                or img_name
                or variant.get("price_czk") is not None
            ):
                continue

            variant_stock = variant.get("stock")
            if variant_stock is None:
                variant_stock = 1
            variant_price = variant.get("price_czk")
            if variant_price is None:
                variant_price = _auto_variant_price(
                    category_name=category_name,
                    category_slug=category_slug,
                    product_name=name,
                    product_description=description,
                    variant_name=variant.get("variant_name"),
                    variant_description=variant.get("description"),
                )
            v_obj = ProductVariant(
                product_id=product.id,
                variant_name=variant.get("variant_name"),
                wrist_size=variant.get("wrist_size"),
                description=variant.get("description"),
                price_czk=variant_price,
                stock=variant_stock,
                image=img_name,
            )
            db.add(v_obj)

            for ef in variant.get("extra_files") or []:
                extra_assets = _save_main_image_assets(ef)
                saved_full = _normalize_upload_filename(extra_assets.get("full"))
                if saved_full:
                    db.add(ProductVariantMedia(variant=v_obj, filename=saved_full))

        for mf in files.get("media", []):
            if not mf or not mf.filename:
                continue
            media_type = _detect_media_type(mf.filename, getattr(mf, "content_type", None))
            saved_name = _save_upload_file(mf)
            db.add(ProductMedia(product_id=product.id, filename=saved_name, media_type=media_type))

        db.commit()
        db.refresh(product)
        return get_product(db, product.id) or _product_dict(product)
    except Exception:
        db.rollback()
        raise


def _collect_variant_files(variants: Iterable[ProductVariant]) -> set[str]:
    files: set[str] = set()
    for variant in variants:
        if variant.image:
            files.update(_variant_related_files(variant.image))
        for media in list(variant.media or []):
            if media.filename:
                files.update(_variant_related_files(media.filename))
    return files


def _candidate_upload_paths(filename: str | None) -> list[str]:
    normalized = _normalize_upload_filename(filename)
    if not normalized:
        return []
    candidates = {
        normalized,
        f"/static/uploads/{normalized}",
        f"static/uploads/{normalized}",
        Path(normalized).name,
    }
    return [c for c in candidates if c]


def _is_protected_upload_path(filename: str | None) -> bool:
    normalized = _normalize_upload_filename(filename)
    if not normalized:
        return False
    lower = normalized.lower()
    return any(lower.startswith(prefix) for prefix in PROTECTED_UPLOAD_PREFIXES)


def _is_file_referenced(db: Session, filename: str | None) -> bool:
    candidates = _candidate_upload_paths(filename)
    if not candidates:
        return False
    return any(
        [
            db.query(Product.id).filter(or_(*[Product.image == c for c in candidates])).first(),
            db.query(ProductVariant.id).filter(or_(*[ProductVariant.image == c for c in candidates])).first(),
            db.query(ProductMedia.id).filter(or_(*[ProductMedia.filename == c for c in candidates])).first(),
            db.query(ProductVariantMedia.id)
            .filter(or_(*[ProductVariantMedia.filename == c for c in candidates]))
            .first(),
            db.query(MediaInboxItem.id).filter(or_(*[MediaInboxItem.webp_path == c for c in candidates])).first(),
            db.query(MediaSecondInboxItem.id)
            .filter(or_(*[MediaSecondInboxItem.webp_path == c for c in candidates]))
            .first(),
        ]
    )


def _remove_files(db: Session, filenames: Iterable[str]) -> None:
    try:
        db.flush()
    except Exception:
        pass
    for fname in filenames:
        if not fname:
            continue
        normalized = _normalize_upload_filename(fname)
        if not normalized:
            continue
        if _is_protected_upload_path(normalized):
            continue
        if _is_file_referenced(db, normalized):
            continue
        try:
            path = UPLOAD_DIR / normalized
            if path.exists():
                path.unlink()
        except Exception:
            pass


def update_product(
    db: Session,
    *,
    product_id: int,
    payload: dict[str, Any],
    form: dict[str, Any] | None,
    files: dict[str, list[UploadFile]] | None,
) -> dict[str, Any] | None:
    product = (
        db.query(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.variants).selectinload(ProductVariant.media),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        return None

    data = payload or {}
    form = form or {}
    files = files or {}

    clear_variants_flag = str(form.get("clear_variants") or data.get("clear_variants") or "").strip() == "1"
    delete_image_flag = str(form.get("delete_image") or data.get("delete_image") or "").strip() == "1"

    name = (data.get("name") or form.get("name") or "").strip()
    description = (data.get("description") or form.get("description") or "").strip()
    seo_title = (data.get("seo_title") or form.get("seo_title") or "").strip()
    seo_description = (data.get("seo_description") or form.get("seo_description") or "").strip()
    seo_keywords = (data.get("seo_keywords") or form.get("seo_keywords") or "").strip()
    price_raw = str(
        data.get("price")
        or data.get("price_czk")
        or form.get("price")
        or form.get("price_czk")
        or ""
    ).strip()
    stock_raw = str(data.get("stock") or form.get("stock") or "").strip()
    active_raw = data.get("active") if "active" in data else form.get("active")
    category_id = data.get("category_id") or form.get("category_id")
    wrist_size_raw = (
        data.get("wrist_size")
        or data.get("wrist_sizes")
        or form.get("wrist_size")
        or form.get("wrist_sizes")
        or ""
    ).strip()
    wrist_size_present = any(key in data or key in form for key in ("wrist_size", "wrist_sizes"))

    variants_payload, variants_explicit = _parse_variants_from_json(data)
    if form:
        form_variants, explicit_form = _parse_variants_from_form(form, files, is_add_request=False)
        if explicit_form:
            variants_payload = form_variants
            variants_explicit = True

    if clear_variants_flag:
        variants_payload = []
        variants_explicit = True

    variants_payload = _dedupe_variants(variants_payload)

    try:
        if name:
            product.name = name
        if description or "description" in data or "description" in form:
            product.description = description or None
        if "seo_title" in data or "seo_title" in form:
            product.seo_title = seo_title or None
        if "seo_description" in data or "seo_description" in form:
            product.seo_description = seo_description or None
        if "seo_keywords" in data or "seo_keywords" in form:
            product.seo_keywords = seo_keywords or None
        if wrist_size_present:
            product.wrist_size = wrist_size_raw or None
        if price_raw:
            try:
                product.price_czk = float(price_raw)
            except ValueError as exc:
                raise ValueError("Invalid price") from exc
        if stock_raw:
            try:
                stock = int(stock_raw)
                if stock < 0:
                    raise ValueError
                product.stock = stock
            except ValueError as exc:
                raise ValueError("Invalid stock") from exc
        if "active" in data or "active" in form:
            active_val = _to_bool(active_raw, default=None)
            if active_val is not None:
                product.active = active_val
        if product.stock is not None and int(product.stock) <= 0:
            product.active = False
        if category_id:
            try:
                product.category_id = int(category_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid category_id") from exc

        if delete_image_flag:
            old_main_files = _collect_main_image_files(product)
            if old_main_files:
                _remove_files(db, old_main_files)
                for filename in old_main_files:
                    _delete_product_media_row(db, product_id=product.id, filename=filename)
            _replace_main_media_rows(db, product_id=product.id, assets=None)
            product.image = None

        image_file = (files.get("image") or [None])[0]
        if image_file and image_file.filename:
            old_main_files = _collect_main_image_files(product)
            new_assets = _save_main_image_assets(image_file)
            new_main_files = {
                _normalize_upload_filename(new_assets.get("original")),
                _normalize_upload_filename(new_assets.get("full")),
                _normalize_upload_filename(new_assets.get("thumb")),
            }
            new_main_files.discard(None)

            product.image = new_assets.get("full")
            _replace_main_media_rows(db, product_id=product.id, assets=new_assets)

            for filename in old_main_files:
                _delete_product_media_row(db, product_id=product.id, filename=filename)
            _remove_files(db, old_main_files - new_main_files)

        if variants_explicit:
            effective_category_name, effective_category_slug = _category_context(
                db,
                _to_int(getattr(product, "category_id", None), default=None),
            )
            old_variants = list(product.variants or [])
            existing_files = _collect_variant_files(old_variants)
            existing_by_id = {
                int(v.id): v for v in old_variants if getattr(v, "id", None) is not None
            }
            old_variant_ids = set(existing_by_id.keys())
            kept_variant_ids: set[int] = set()
            new_files: set[str] = set()

            for idx, variant in enumerate(variants_payload):
                requested_id = _to_int(variant.get("id"), default=None)
                v_obj = existing_by_id.get(requested_id) if requested_id is not None else None
                if v_obj is None and requested_id is None and idx < len(old_variants):
                    fallback = old_variants[idx]
                    fallback_id = _to_int(getattr(fallback, "id", None), default=None)
                    if fallback_id is None or fallback_id not in kept_variant_ids:
                        v_obj = fallback

                existing_image = _normalize_upload_filename(getattr(v_obj, "image", None))
                img_name = _normalize_upload_filename(
                    variant.get("image") or variant.get("existing_image") or existing_image
                )
                if variant.get("image_file"):
                    image_assets = _save_main_image_assets(variant["image_file"])
                    img_name = _normalize_upload_filename(image_assets.get("full")) or img_name

                if not (
                    variant.get("variant_name")
                    or variant.get("wrist_size")
                    or img_name
                    or variant.get("price_czk") is not None
                ):
                    continue

                if img_name:
                    new_files.update(_variant_related_files(img_name))

                payload_existing_extra = [
                    v
                    for v in (
                        _normalize_upload_filename(ee) for ee in (variant.get("existing_extra") or [])
                    )
                    if v
                ]
                if payload_existing_extra:
                    extra_existing = payload_existing_extra
                else:
                    extra_existing = []
                    if v_obj is not None:
                        for vm in list(v_obj.media or []):
                            normalized = _normalize_upload_filename(vm.filename)
                            if normalized:
                                extra_existing.append(normalized)

                extra_saved: list[str] = []
                for ef in variant.get("extra_files") or []:
                    extra_assets = _save_main_image_assets(ef)
                    saved_full = _normalize_upload_filename(extra_assets.get("full"))
                    if saved_full:
                        extra_saved.append(saved_full)

                for existing_name in extra_existing:
                    new_files.update(_variant_related_files(existing_name))
                for saved_name in extra_saved:
                    new_files.update(_variant_related_files(saved_name))

                variant_stock = variant.get("stock")
                if variant_stock is None:
                    variant_stock = 1
                variant_price = variant.get("price_czk")
                if variant_price is None:
                    variant_price = _auto_variant_price(
                        category_name=effective_category_name,
                        category_slug=effective_category_slug,
                        product_name=product.name,
                        product_description=product.description,
                        variant_name=variant.get("variant_name"),
                        variant_description=variant.get("description"),
                    )
                if v_obj is None:
                    v_obj = ProductVariant(
                        product_id=product.id,
                        variant_name=variant.get("variant_name"),
                        wrist_size=variant.get("wrist_size"),
                        description=variant.get("description"),
                        price_czk=variant_price,
                        stock=variant_stock,
                        image=img_name,
                    )
                    db.add(v_obj)
                    db.flush()
                else:
                    v_obj.product_id = product.id
                    v_obj.variant_name = variant.get("variant_name")
                    v_obj.wrist_size = variant.get("wrist_size")
                    v_obj.description = variant.get("description")
                    v_obj.price_czk = variant_price
                    v_obj.stock = variant_stock
                    v_obj.image = img_name
                    for vm in list(v_obj.media or []):
                        db.delete(vm)

                current_id = _to_int(getattr(v_obj, "id", None), default=None)
                if current_id is not None:
                    kept_variant_ids.add(current_id)

                for fn in extra_existing:
                    db.add(ProductVariantMedia(variant=v_obj, filename=fn))
                for fn in extra_saved:
                    db.add(ProductVariantMedia(variant=v_obj, filename=fn))

            for old_variant in old_variants:
                old_id = _to_int(getattr(old_variant, "id", None), default=None)
                if old_id is None or old_id in kept_variant_ids:
                    continue
                db.delete(old_variant)

            _remove_files(db, existing_files - new_files)

        for mf in files.get("media", []):
            if not mf or not mf.filename:
                continue
            media_type = _detect_media_type(mf.filename, getattr(mf, "content_type", None))
            saved_name = _save_upload_file(mf)
            db.add(ProductMedia(product_id=product.id, filename=saved_name, media_type=media_type))

        db.commit()
        db.refresh(product)
        return get_product(db, product.id) or _product_dict(product)
    except Exception:
        db.rollback()
        raise


def delete_product(db: Session, product_id: int, *, commit: bool = True) -> bool:
    product = (
        db.query(Product)
        .options(
            selectinload(Product.media),
            selectinload(Product.variants).selectinload(ProductVariant.media),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        return False

    try:
        files_to_remove: set[str] = set()
        if product.image:
            files_to_remove.add(product.image)

        for media in list(product.media or []):
            if media.filename:
                files_to_remove.add(media.filename)
            db.delete(media)

        for variant in list(product.variants or []):
            if variant.image:
                files_to_remove.update(_variant_related_files(variant.image))
            for vm in list(variant.media or []):
                if vm.filename:
                    files_to_remove.update(_variant_related_files(vm.filename))
                db.delete(vm)
            db.delete(variant)

        db.delete(product)
        if commit:
            db.commit()

        _remove_files(db, files_to_remove)
        return True
    except Exception:
        db.rollback()
        raise
