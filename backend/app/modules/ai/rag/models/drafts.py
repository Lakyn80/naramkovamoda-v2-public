from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime

class DraftProduct(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID

    draft_title: str
    draft_description: str
    product_type: str  # např. "bracelet", "candle", "other"

    confidence: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DraftVariant(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID

    variant_key: str  # např. "color:pink" nebo "size:17cm"
    title_suffix: Optional[str] = None
    description_delta: Optional[str] = None

    media_asset_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
