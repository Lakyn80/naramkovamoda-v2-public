from __future__ import annotations

import io
import uuid

import app.core.paths as core_paths
import app.modules.media_inbox.router as media_inbox_router
import app.modules.media_second_inbox.router as media_second_router
import app.modules.products.service as product_service
from app.db.models import (
    MediaInboxItem,
    MediaSecondInboxItem,
    Product,
    ProductMedia,
    ProductVariant,
    ProductVariantMedia,
)


def _fake_convert_to_webp(subdir: str):
    def _inner(_input_path: str) -> str:
        out_dir = core_paths.UPLOAD_DIR / subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{uuid.uuid4().hex}.webp"
        out_path.write_bytes(b"fake-webp")
        return str(out_path)

    return _inner


def _fake_draft(_path: str) -> dict:
    return {
        "title": "Test title",
        "description": "Test description",
        "product_type": "bracelet",
        "combined_tags": ["tag-a", "tag-b"],
    }


def _touch_upload(rel_path: str) -> None:
    path = core_paths.UPLOAD_DIR / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-webp")


def test_media_inbox_upload_and_pending(client, db_session, monkeypatch):
    monkeypatch.setattr(media_inbox_router, "convert_to_webp", _fake_convert_to_webp("inbox_webp"))
    monkeypatch.setattr(media_inbox_router, "generate_draft_for_inbox_image", _fake_draft)

    files = [("files", ("test.jpg", io.BytesIO(b"fake"), "image/jpeg"))]
    response = client.post("/api/media-inbox/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] == 1

    pending = client.get("/api/media-inbox/pending")
    assert pending.status_code == 200
    items = pending.json()["items"]
    assert len(items) == 1

    item = items[0]
    assert item["filename"] == "test.jpg"
    assert item["product_type"] == "bracelet"
    assert item["webp_path"].endswith(".webp")
    assert "uploads/uploads" not in item["webp_path"]

    db_item = db_session.query(MediaInboxItem).first()
    assert db_item is not None
    assert db_item.draft_title == "Test title"
    assert db_item.product_type == "bracelet"


def test_media_inbox_assign_create_product(client, db_session):
    _touch_upload("inbox_webp/x.webp")
    item = MediaInboxItem(
        filename="x.jpg",
        webp_path="inbox_webp/x.webp",
        draft_title="Draft title",
        draft_description="Draft description",
        product_type="bracelet",
        combined_tags=["tag"],
        status="pending",
    )
    db_session.add(item)
    db_session.commit()

    response = client.post(
        "/api/media-inbox/assign",
        json={"items": [{"inbox_id": item.id, "assign_as": "product"}]},
    )
    assert response.status_code == 200
    payload = response.json()
    product_id = payload["product_ids"][0]

    product = db_session.get(Product, product_id)
    assert product is not None
    assert product.name == "Draft title"
    assert float(product.price_czk) == 149.0
    assert product.image
    assert product.image.startswith("catalog_webp/")

    media = db_session.query(ProductMedia).filter_by(product_id=product_id).all()
    assert len(media) == 0

    updated = db_session.get(MediaInboxItem, item.id)
    assert updated is not None
    assert updated.status == "assigned"
    assert updated.assigned_product_id == product_id


def test_media_inbox_assign_variant(client, db_session):
    product = Product(name="Base", description=None, price_czk=0, stock=0)
    db_session.add(product)
    db_session.commit()

    _touch_upload("inbox_webp/y.webp")
    item = MediaInboxItem(
        filename="y.jpg",
        webp_path="inbox_webp/y.webp",
        draft_title="Variant title",
        draft_description="Variant description",
        product_type="bracelet",
        combined_tags=["přívěsek"],
        status="pending",
    )
    db_session.add(item)
    db_session.commit()

    response = client.post(
        "/api/media-inbox/assign",
        json={
            "items": [
                {
                    "inbox_id": item.id,
                    "assign_as": "variant",
                    "parent_product_id": product.id,
                }
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    variant_id = payload["variant_ids"][0]

    variant = db_session.get(ProductVariant, variant_id)
    assert variant is not None
    assert variant.product_id == product.id
    assert variant.variant_name == "Variant title"
    assert float(variant.price_czk) == 159.0
    assert variant.image
    assert variant.image.startswith("catalog_webp/")

    updated = db_session.get(MediaInboxItem, item.id)
    assert updated is not None
    assert updated.status == "assigned"
    assert updated.assigned_variant_id == variant_id


def test_media_second_upload_and_pending(client, db_session, monkeypatch):
    monkeypatch.setattr(media_second_router, "convert_to_webp", _fake_convert_to_webp("second_inbox_webp"))

    files = [("files", ("test.png", io.BytesIO(b"fake"), "image/png"))]
    response = client.post("/api/media-second/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["imported"] == 1

    pending = client.get("/api/media-second/pending")
    assert pending.status_code == 200
    items = pending.json()["items"]
    assert len(items) == 1

    db_item = db_session.query(MediaSecondInboxItem).first()
    assert db_item is not None


def test_media_second_assign_product(client, db_session):
    product = Product(name="Base", description=None, price_czk=0, stock=0)
    db_session.add(product)
    db_session.commit()

    _touch_upload("second_inbox_webp/a.webp")
    item = MediaSecondInboxItem(webp_path="second_inbox_webp/a.webp", status="pending")
    db_session.add(item)
    db_session.commit()

    response = client.post(
        "/api/media-second/assign",
        json={"items": [{"second_inbox_id": item.id, "assign_to_product": product.id}]},
    )
    assert response.status_code == 200

    media = db_session.query(ProductMedia).filter_by(product_id=product.id).all()
    assert len(media) == 1
    assert media[0].filename
    assert media[0].filename.startswith("catalog_webp/")

    updated = db_session.get(MediaSecondInboxItem, item.id)
    assert updated is not None
    assert updated.status == "assigned"


def test_media_second_assign_variant(client, db_session):
    product = Product(name="Base", description=None, price_czk=0, stock=0)
    db_session.add(product)
    db_session.commit()

    variant = ProductVariant(product_id=product.id, variant_name="Var", stock=0)
    db_session.add(variant)
    db_session.commit()

    _touch_upload("second_inbox_webp/b.webp")
    item = MediaSecondInboxItem(webp_path="second_inbox_webp/b.webp", status="pending")
    db_session.add(item)
    db_session.commit()

    response = client.post(
        "/api/media-second/assign",
        json={"items": [{"second_inbox_id": item.id, "assign_to_variant": variant.id}]},
    )
    assert response.status_code == 200

    media = db_session.query(ProductVariantMedia).filter_by(variant_id=variant.id).all()
    assert len(media) == 1
    assert media[0].filename
    assert media[0].filename.startswith("catalog_webp/")

    updated = db_session.get(MediaSecondInboxItem, item.id)
    assert updated is not None
    assert updated.status == "assigned"


def test_normalize_upload_filename():
    assert product_service._normalize_upload_filename("/static/uploads/uploads/abc.webp") == "abc.webp"
    assert product_service._normalize_upload_filename("static/uploads/xyz.png") == "xyz.png"
    assert product_service._normalize_upload_filename("uploads/uploads/foo.jpg") == "foo.jpg"
    assert product_service._normalize_upload_filename("uploads/bar.jpg") == "bar.jpg"
    assert product_service._normalize_upload_filename("bar.jpg") == "bar.jpg"
