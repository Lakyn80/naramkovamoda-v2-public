from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

# HEIC/HEIF support (iPhone)
try:
    from pillow_heif import register_heif_opener  # type: ignore

    register_heif_opener()
except Exception:
    pass

from app.core.paths import UPLOAD_DIR

SECOND_INBOX_WEBP_DIR = UPLOAD_DIR / "second_inbox_webp"
DEFAULT_QUALITY = 72
COUNTER_FILENAME = ".counter"


def _normalize_base_name(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return "naramkovamoda"
    try:
        normalized = unicodedata.normalize("NFKD", raw)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    except Exception:
        normalized = raw
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "naramkovamoda"


def _read_counter(target_dir: Path) -> int:
    try:
        raw = (target_dir / COUNTER_FILENAME).read_text(encoding="utf-8").strip()
        return int(raw)
    except Exception:
        return 0


def _scan_max_index(target_dir: Path) -> int:
    max_val = 0
    try:
        for item in target_dir.glob("*.webp"):
            match = re.search(r"_(\d+)\.webp$", item.name.lower())
            if match:
                max_val = max(max_val, int(match.group(1)))
    except Exception:
        pass
    return max_val


def _next_index(target_dir: Path) -> int:
    current = _read_counter(target_dir)
    existing = _scan_max_index(target_dir)
    return max(current, existing) + 1


def _write_counter(target_dir: Path, value: int) -> None:
    try:
        (target_dir / COUNTER_FILENAME).write_text(str(value), encoding="utf-8")
    except Exception:
        pass


def _choose_save_kwargs(src: Path, img: Image.Image, quality: int) -> dict:
    ext = src.suffix.lower()
    save: dict = {
        "format": "WEBP",
        "method": 6,
        "optimize": True,
    }

    icc = img.info.get("icc_profile")
    if icc:
        save["icc_profile"] = icc
    try:
        exif = img.getexif()
        if exif:
            save["exif"] = exif.tobytes()
    except Exception:
        pass

    if ext in (".jpg", ".jpeg", ".heic", ".heif"):
        save["lossless"] = False
        save["quality"] = int(quality)
    elif ext == ".png":
        if img.mode in ("RGBA", "LA"):
            save["lossless"] = True
        else:
            save["lossless"] = True
            save["quality"] = 90
    else:
        save["lossless"] = False
        save["quality"] = int(quality)

    return save


def _resize_if_needed(img: Image.Image, max_width: int | None) -> Image.Image:
    if max_width and max_width > 0 and img.width > max_width:
        new_h = max(1, int(img.height * (max_width / img.width)))
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
    return img


def convert_to_webp(input_path: str, *, quality: int = DEFAULT_QUALITY, max_width: int | None = None) -> str:
    """
    Convert input image to WebP, save under static/uploads/second_inbox_webp,
    delete the original, and return the new WebP absolute path.
    """
    src = Path(input_path)
    SECOND_INBOX_WEBP_DIR.mkdir(parents=True, exist_ok=True)
    base_name = "nm"
    next_index = _next_index(SECOND_INBOX_WEBP_DIR)
    out_name = f"{base_name}_{next_index}.webp"
    out_path = SECOND_INBOX_WEBP_DIR / out_name
    while out_path.exists():
        next_index += 1
        out_name = f"{base_name}_{next_index}.webp"
        out_path = SECOND_INBOX_WEBP_DIR / out_name

    try:
        with Image.open(src) as img:
            img = ImageOps.exif_transpose(img)
            img = _resize_if_needed(img, max_width)

            if img.mode in ("I;16", "I", "F"):
                img = img.convert("RGB")
            elif img.mode in ("P", "LA"):
                img = img.convert("RGBA")
            elif img.mode == "CMYK":
                img = img.convert("RGB")

            save_kwargs = _choose_save_kwargs(src, img, quality)
            img.save(out_path, **save_kwargs)
    except (UnidentifiedImageError, OSError) as exc:
        try:
            src.unlink()
        except Exception:
            pass
        raise ValueError("Unsupported or corrupted image file") from exc

    try:
        src.unlink()
    except Exception:
        pass

    _write_counter(SECOND_INBOX_WEBP_DIR, next_index)
    return str(out_path)
