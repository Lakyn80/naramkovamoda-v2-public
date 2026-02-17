from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class SoldProduct(Base):
    __tablename__ = "sold_product"

    id = Column(Integer, primary_key=True)
    original_product_id = Column(Integer)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image = Column(String(255), nullable=True)
    price = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    customer_name = Column(String(100))
    customer_email = Column(String(100))
    customer_address = Column(Text)
    note = Column(Text)
    payment_type = Column(String(50))
    sold_at = Column(DateTime, default=datetime.utcnow)
