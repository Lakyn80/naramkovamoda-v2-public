from __future__ import annotations

import os
from sqlalchemy.orm import Session

from app.core.paths import UPLOAD_DIR

from app.db.models import ProductMedia


def delete_media(db: Session, media_id: int) -> dict[str, str] | None:
    media = db.get(ProductMedia, media_id)
    if not media:
        return None

    filename = media.filename
    if filename:
        file_path = UPLOAD_DIR / filename
        try:
            if file_path.exists():
                os.remove(file_path)
        except Exception:
            pass

    db.delete(media)
    db.commit()

    return {"message": "Médium bylo úspěšně smazáno."}
