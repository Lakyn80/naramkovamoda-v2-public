from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import require_admin
from .service import delete_media

router = APIRouter(prefix="/api/media", tags=["media"])


@router.delete("/{media_id}")
async def delete_media_endpoint(
    media_id: int,
    _user=Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Legacy: DELETE /api/media/<int:media_id>."""
    data = delete_media(db, media_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data
