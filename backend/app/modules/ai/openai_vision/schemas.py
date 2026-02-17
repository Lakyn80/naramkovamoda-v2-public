from __future__ import annotations

from typing import List

from pydantic import BaseModel


class OpenAIVisionResult(BaseModel):
    title: str
    description: str
    tags: List[str]
    model: str
