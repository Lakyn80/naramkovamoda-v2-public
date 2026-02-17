"""Fix SERIAL primary keys for SQLite media inbox tables.

Run with:
    python -m app.db.migrations.fix_media_inbox_id_sqlite
"""

from sqlalchemy import text

from app.db.session import engine


def _table_needs_fix(conn, table_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    for row in rows:
        # row = (cid, name, type, notnull, dflt_value, pk)
        if row[1] == "id":
            col_type = (row[2] or "").upper()
            pk = row[5]
            return pk == 1 and col_type != "INTEGER"
    return False


def _rebuild_media_inbox(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE media_inbox_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NULL,
                webp_path TEXT NOT NULL,
                draft_title TEXT NULL,
                draft_description TEXT NULL,
                product_type TEXT NULL,
                combined_tags JSON NULL,
                status TEXT NOT NULL,
                assigned_product_id INT NULL,
                assigned_variant_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO media_inbox_items_new (
                filename,
                webp_path,
                draft_title,
                draft_description,
                product_type,
                combined_tags,
                status,
                assigned_product_id,
                assigned_variant_id,
                created_at
            )
            SELECT
                filename,
                webp_path,
                draft_title,
                draft_description,
                product_type,
                combined_tags,
                status,
                assigned_product_id,
                assigned_variant_id,
                created_at
            FROM media_inbox_items
            """
        )
    )
    conn.execute(text("DROP TABLE media_inbox_items"))
    conn.execute(text("ALTER TABLE media_inbox_items_new RENAME TO media_inbox_items"))


def _rebuild_media_second(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE media_second_inbox_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webp_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO media_second_inbox_items_new (
                webp_path,
                status,
                created_at
            )
            SELECT
                webp_path,
                status,
                created_at
            FROM media_second_inbox_items
            """
        )
    )
    conn.execute(text("DROP TABLE media_second_inbox_items"))
    conn.execute(text("ALTER TABLE media_second_inbox_items_new RENAME TO media_second_inbox_items"))


def upgrade() -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        if _table_needs_fix(conn, "media_inbox_items"):
            _rebuild_media_inbox(conn)
        if _table_needs_fix(conn, "media_second_inbox_items"):
            _rebuild_media_second(conn)


def main() -> None:
    upgrade()


if __name__ == "__main__":
    main()
