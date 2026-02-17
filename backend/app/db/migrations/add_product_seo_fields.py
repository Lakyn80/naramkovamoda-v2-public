"""Add SEO fields to product table.

Run with:
    python -m app.db.migrations.add_product_seo_fields
"""

from sqlalchemy import text

from app.db.session import engine


def _sqlite_existing_columns(conn) -> set[str]:
    rows = conn.execute(text("PRAGMA table_info(product)")).fetchall()
    return {r[1] for r in rows}


def upgrade() -> None:
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            existing = _sqlite_existing_columns(conn)
            if "seo_title" not in existing:
                conn.execute(text("ALTER TABLE product ADD COLUMN seo_title TEXT NULL"))
            if "seo_description" not in existing:
                conn.execute(text("ALTER TABLE product ADD COLUMN seo_description TEXT NULL"))
            if "seo_keywords" not in existing:
                conn.execute(text("ALTER TABLE product ADD COLUMN seo_keywords TEXT NULL"))
            return

        statements = [
            "ALTER TABLE product ADD COLUMN IF NOT EXISTS seo_title TEXT NULL",
            "ALTER TABLE product ADD COLUMN IF NOT EXISTS seo_description TEXT NULL",
            "ALTER TABLE product ADD COLUMN IF NOT EXISTS seo_keywords TEXT NULL",
        ]
        for stmt in statements:
            conn.execute(text(stmt))


def main() -> None:
    upgrade()


if __name__ == "__main__":
    main()
