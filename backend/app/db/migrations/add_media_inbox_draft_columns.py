"""Přidá draft_title a draft_description do media_inbox_items, pokud chybí.

Spustit:
    python -m app.db.migrations.add_media_inbox_draft_columns
"""

from sqlalchemy import text

from app.db.session import engine


def _sqlite_columns(conn) -> set[str]:
    rows = conn.execute(text("PRAGMA table_info(media_inbox_items)")).fetchall()
    return {r[1] for r in rows}


def upgrade() -> None:
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            existing = _sqlite_columns(conn)
            if "draft_title" not in existing:
                conn.execute(text("ALTER TABLE media_inbox_items ADD COLUMN draft_title TEXT NULL"))
            if "draft_description" not in existing:
                conn.execute(text("ALTER TABLE media_inbox_items ADD COLUMN draft_description TEXT NULL"))
            return

        # PostgreSQL
        for col in ("draft_title", "draft_description"):
            conn.execute(text(
                f"ALTER TABLE media_inbox_items ADD COLUMN IF NOT EXISTS {col} TEXT NULL"
            ))


def main() -> None:
    upgrade()
    print("OK: draft_title / draft_description zkontrolovány.")


if __name__ == "__main__":
    main()
