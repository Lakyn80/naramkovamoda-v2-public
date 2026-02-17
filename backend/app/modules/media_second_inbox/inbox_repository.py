from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import MediaSecondInboxItem


PENDING = "pending"
ASSIGNED = "assigned"


def add_inbox_item(
    db: Session,
    *,
    webp_path: str,
    filename: str | None = None,
) -> MediaSecondInboxItem:
    item = MediaSecondInboxItem(webp_path=webp_path, filename=filename, status=PENDING)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_pending_items(db: Session) -> list[MediaSecondInboxItem]:
    return (
        db.query(MediaSecondInboxItem)
        .filter(MediaSecondInboxItem.status == PENDING)
        .order_by(MediaSecondInboxItem.id.desc())
        .all()
    )


def mark_assigned(db: Session, item_id: int) -> MediaSecondInboxItem | None:
    item = db.get(MediaSecondInboxItem, item_id)
    if not item:
        return None
    item.status = ASSIGNED
    db.commit()
    db.refresh(item)
    return item
