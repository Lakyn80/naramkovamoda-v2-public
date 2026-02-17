from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class TemplateExample(BaseModel):
    """
    Šablona popisu produktu vytvářená / upravovaná v adminu.
    Později z ní budeme generovat embedding a ukládat ji do Chroma.
    """

    id: UUID = Field(default_factory=uuid4)

    # Jaký typ produktu se podle ní generuje
    product_type: str  # např. "bracelet", "candle", "other"

    # Styl a tón značky (pro filtrování v RAG)
    style: Optional[str] = None      # např. "romantic", "minimalist"
    tone: Optional[str] = None       # např. "jemný", "luxusní"

    # Samotné šablony textu
    title_template: str
    description_template: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
