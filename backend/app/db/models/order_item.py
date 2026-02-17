from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class OrderItem(Base):
    __tablename__ = "order_item"

    id = Column(Integer, primary_key=True)
    product_name = Column(String(150), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)

    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)

    order = relationship("Order", back_populates="items")
