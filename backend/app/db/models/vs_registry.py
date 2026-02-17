from __future__ import annotations

from sqlalchemy import Column, String

from app.db.base import Base


class VsRegistry(Base):
    __tablename__ = "vs_registry"

    vs = Column(String, primary_key=True)
