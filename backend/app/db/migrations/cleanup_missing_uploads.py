"""Clean DB references to missing upload files.

Run with:
    python -m app.db.migrations.cleanup_missing_uploads
"""

from pathlib import Path

from sqlalchemy import bindparam, text

from app.core.paths import UPLOAD_DIR
from app.db.session import engine


def _normalize_path(path: str) -> str:
    p = str(path).replace("\\", "/")
    if p.startswith("/static/uploads/"):
        p = p.split("/static/uploads/", 1)[1]
    elif p.startswith("static/uploads/"):
        p = p.split("static/uploads/", 1)[1]
    return p.lstrip("/")


def _file_exists(rel_path: str) -> bool:
    return (UPLOAD_DIR / rel_path).exists()


def cleanup() -> None:
    with engine.begin() as conn:
        # product.image -> set NULL if missing
        rows = conn.execute(text("SELECT id, image FROM product WHERE image IS NOT NULL")).fetchall()
        missing_product_ids = []
        for pid, image in rows:
            rel = _normalize_path(image)
            if not _file_exists(rel):
                missing_product_ids.append(pid)
        if missing_product_ids:
            stmt = text("UPDATE product SET image = NULL WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            conn.execute(stmt, {"ids": missing_product_ids})

        # product_media.filename -> delete rows if missing
        rows = conn.execute(text("SELECT id, filename FROM product_media")).fetchall()
        missing_media_ids = []
        for mid, filename in rows:
            rel = _normalize_path(filename)
            if not _file_exists(rel):
                missing_media_ids.append(mid)
        if missing_media_ids:
            stmt = text("DELETE FROM product_media WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            conn.execute(stmt, {"ids": missing_media_ids})

        # product_variant.image -> set NULL if missing
        rows = conn.execute(text("SELECT id, image FROM product_variant WHERE image IS NOT NULL")).fetchall()
        missing_variant_ids = []
        for vid, image in rows:
            rel = _normalize_path(image)
            if not _file_exists(rel):
                missing_variant_ids.append(vid)
        if missing_variant_ids:
            stmt = text("UPDATE product_variant SET image = NULL WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            conn.execute(stmt, {"ids": missing_variant_ids})

        # product_variant_media.filename -> delete rows if missing
        rows = conn.execute(text("SELECT id, filename FROM product_variant_media")).fetchall()
        missing_variant_media_ids = []
        for mid, filename in rows:
            rel = _normalize_path(filename)
            if not _file_exists(rel):
                missing_variant_media_ids.append(mid)
        if missing_variant_media_ids:
            stmt = text("DELETE FROM product_variant_media WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            conn.execute(stmt, {"ids": missing_variant_media_ids})

        # media_inbox_items.webp_path -> delete pending rows if missing
        rows = conn.execute(
            text("SELECT id, webp_path, status FROM media_inbox_items WHERE webp_path IS NOT NULL")
        ).fetchall()
        missing_inbox_ids = []
        for iid, webp_path, status in rows:
            rel = _normalize_path(webp_path)
            if not _file_exists(rel) and status == "pending":
                missing_inbox_ids.append(iid)
        if missing_inbox_ids:
            stmt = text("DELETE FROM media_inbox_items WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            conn.execute(stmt, {"ids": missing_inbox_ids})

        # media_second_inbox_items.webp_path -> delete pending rows if missing
        rows = conn.execute(
            text("SELECT id, webp_path, status FROM media_second_inbox_items WHERE webp_path IS NOT NULL")
        ).fetchall()
        missing_second_ids = []
        for iid, webp_path, status in rows:
            rel = _normalize_path(webp_path)
            if not _file_exists(rel) and status == "pending":
                missing_second_ids.append(iid)
        if missing_second_ids:
            stmt = text("DELETE FROM media_second_inbox_items WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            conn.execute(stmt, {"ids": missing_second_ids})


def main() -> None:
    cleanup()


if __name__ == "__main__":
    main()
