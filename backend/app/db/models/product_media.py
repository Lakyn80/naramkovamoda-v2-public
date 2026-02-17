from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProductMedia(Base):
    __tablename__ = "product_media"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    media_type = Column(String(20), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)

    product = relationship("Product", back_populates="media")
