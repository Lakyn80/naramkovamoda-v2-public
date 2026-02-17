from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(150), nullable=True, unique=True)
    group = Column(String(100), nullable=True)

    products = relationship("Product", back_populates="category")
