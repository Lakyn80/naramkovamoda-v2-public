from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProductVariant(Base):
    __tablename__ = "product_variant"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    variant_name = Column(String(150), nullable=True)
    wrist_size = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    price_czk = Column(Numeric(10, 2), nullable=True)
    image = Column(String(255), nullable=True)
    stock = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="variants")
    media = relationship(
        "ProductVariantMedia",
        back_populates="variant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
