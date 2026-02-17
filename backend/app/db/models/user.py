from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
