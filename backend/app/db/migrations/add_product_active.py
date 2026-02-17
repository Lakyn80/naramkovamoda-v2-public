"""Add active flag to product table.

Run with:
    python -m app.db.migrations.add_product_active
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
            if "active" not in existing:
                conn.execute(text("ALTER TABLE product ADD COLUMN active INTEGER NOT NULL DEFAULT 1"))
            return

        conn.execute(text("ALTER TABLE product ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE"))


def main() -> None:
    upgrade()


if __name__ == "__main__":
    main()
