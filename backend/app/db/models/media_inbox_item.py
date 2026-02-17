from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.db.base import Base


class MediaInboxItem(Base):
    __tablename__ = "media_inbox_items"

    id = Column(Integer, primary_key=True)
    filename = Column(Text, nullable=True)
    webp_path = Column(Text, nullable=False)
    draft_title = Column(Text, nullable=True)
    draft_description = Column(Text, nullable=True)
    product_type = Column(Text, nullable=True)
    combined_tags = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    assigned_product_id = Column(Integer, nullable=True)
    assigned_variant_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
