from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price_czk = Column(Numeric(10, 2), nullable=False)
    image = Column(String(255), nullable=True)
    wrist_size = Column(String(50), nullable=True)
    stock = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    seo_title = Column(String(180), nullable=True)
    seo_description = Column(Text, nullable=True)
    seo_keywords = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    media = relationship(
        "ProductMedia",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
