from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Numeric, String, Integer

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True)
    vs = Column(String(32), index=True, nullable=False)
    amount_czk = Column(Numeric(10, 2), nullable=False)
    reference = Column(String(255), nullable=True)
    status = Column(String(32), default="received")
    received_at = Column(DateTime, default=datetime.utcnow)
