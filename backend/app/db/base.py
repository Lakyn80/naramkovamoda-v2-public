"""Database base class (placeholder)."""

try:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()
except Exception:  # pragma: no cover - optional dependency
    Base = object
