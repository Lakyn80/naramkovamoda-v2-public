from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProductVariantMedia(Base):
    __tablename__ = "product_variant_media"

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey("product_variant.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)

    variant = relationship("ProductVariant", back_populates="media")
