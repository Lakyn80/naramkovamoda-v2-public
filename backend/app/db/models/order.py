from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True)
    vs = Column(String(10), unique=True, index=True, nullable=True)
    total_czk = Column(Numeric(10, 2), nullable=True)
    status = Column(String(32), nullable=False, default="awaiting_payment")

    customer_name = Column(String(120), nullable=False)
    customer_email = Column(String(120), nullable=False)
    customer_address = Column(Text, nullable=False)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete",
    )
