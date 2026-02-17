"""Add metadata columns to media_second_inbox_items.

Run with:
    python -m app.db.migrations.add_media_second_inbox_columns
"""

from sqlalchemy import text

from app.db.session import engine


def _sqlite_existing_columns(conn) -> set[str]:
    rows = conn.execute(text("PRAGMA table_info(media_second_inbox_items)")).fetchall()
    return {r[1] for r in rows}


def upgrade() -> None:
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            existing = _sqlite_existing_columns(conn)
            if "filename" not in existing:
                conn.execute(text("ALTER TABLE media_second_inbox_items ADD COLUMN filename TEXT NULL"))
            if "draft_title" not in existing:
                conn.execute(text("ALTER TABLE media_second_inbox_items ADD COLUMN draft_title TEXT NULL"))
            if "draft_description" not in existing:
                conn.execute(text("ALTER TABLE media_second_inbox_items ADD COLUMN draft_description TEXT NULL"))
            if "product_type" not in existing:
                conn.execute(text("ALTER TABLE media_second_inbox_items ADD COLUMN product_type TEXT NULL"))
            if "combined_tags" not in existing:
                conn.execute(text("ALTER TABLE media_second_inbox_items ADD COLUMN combined_tags JSON NULL"))
            return

        statements = [
            "ALTER TABLE media_second_inbox_items ADD COLUMN IF NOT EXISTS filename TEXT NULL",
            "ALTER TABLE media_second_inbox_items ADD COLUMN IF NOT EXISTS draft_title TEXT NULL",
            "ALTER TABLE media_second_inbox_items ADD COLUMN IF NOT EXISTS draft_description TEXT NULL",
            "ALTER TABLE media_second_inbox_items ADD COLUMN IF NOT EXISTS product_type TEXT NULL",
            "ALTER TABLE media_second_inbox_items ADD COLUMN IF NOT EXISTS combined_tags JSON NULL",
        ]
        for stmt in statements:
            conn.execute(text(stmt))


def main() -> None:
    upgrade()


if __name__ == "__main__":
    main()
