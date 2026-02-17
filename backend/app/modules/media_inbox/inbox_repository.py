from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import MediaInboxItem


PENDING = "pending"
APPROVED = "approved"
ASSIGNED = "assigned"


def add_inbox_item(db, filename: str, webp_path: str, draft: dict):
    item = MediaInboxItem(
        filename=filename,
        webp_path=webp_path,
        draft_title=draft.get("title"),
        draft_description=draft.get("description"),
        product_type=draft.get("product_type"),
        combined_tags=draft.get("combined_tags"),
        status="pending",
    )

    db.add(item)
    db.commit()

    # Znovu nacist objekt z DB misto db.refresh (ktery selhava)
    saved = (
        db.query(MediaInboxItem)
        .filter(MediaInboxItem.filename == filename)
        .order_by(MediaInboxItem.id.desc())
        .first()
    )

    return saved


def get_pending_items(db: Session) -> list[MediaInboxItem]:
    return (
        db.query(MediaInboxItem)
        .filter(MediaInboxItem.status == PENDING)
        .order_by(MediaInboxItem.id.desc())
        .all()
    )


def approve_item(db: Session, item_id: int) -> MediaInboxItem | None:
    item = db.get(MediaInboxItem, item_id)
    if not item:
        return None
    item.status = APPROVED
    db.commit()
    db.refresh(item)
    return item


def assign_to_product(db: Session, item_id: int, product_id: int) -> MediaInboxItem | None:
    item = db.get(MediaInboxItem, item_id)
    if not item:
        return None
    item.status = ASSIGNED
    item.assigned_product_id = product_id
    item.assigned_variant_id = None
    db.commit()
    db.refresh(item)
    return item


def assign_to_variant(db: Session, item_id: int, variant_id: int) -> MediaInboxItem | None:
    item = db.get(MediaInboxItem, item_id)
    if not item:
        return None
    item.status = ASSIGNED
    item.assigned_variant_id = variant_id
    item.assigned_product_id = None
    db.commit()
    db.refresh(item)
    return item
