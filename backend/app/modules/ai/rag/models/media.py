# -*- coding: utf-8 -*-
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime


class UploadSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(
        default="uploaded",
        description="uploaded | normalized | analyzed | drafted | confirmed"
    )


class MediaAsset(BaseModel):
    """session_id = product_id (str), obrázky jednotně v backend/static/uploads."""
    id: UUID = Field(default_factory=uuid4)
    session_id: str  # product_id jako session

    path_original: str
    path_webp: Optional[str] = None

    width: Optional[int] = None
    height: Optional[int] = None

    vision_json: Optional[dict] = None
    tags: List[str] = Field(default_factory=list)

    embedding_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "allow"  # např. vision_error při logování
