from __future__ import annotations

from pathlib import Path

from app.db.models import Category, Product
import app.modules.ai.templates.service as templates_service
import app.modules.ai.drafts.service as drafts_service


def test_templates_store_and_list(client, db_session, monkeypatch):
    category = Category(name="Náramky", slug="naramky", group="Test")
    db_session.add(category)
    db_session.commit()

    product = Product(
        name="Test produkt",
        description="Popis produktu",
        price_czk=123.0,
        stock=1,
        category_id=category.id,
    )
    db_session.add(product)
    db_session.commit()

    captured = {}

    def fake_add_template(doc_id, text, metadata):
        captured["doc_id"] = doc_id
        captured["metadata"] = metadata

    monkeypatch.setattr(templates_service, "add_template", fake_add_template)

    res = client.post("/api/ai/templates/store", json={"product_id": product.id})
    assert res.status_code == 200
    payload = res.json()
    assert payload["product_id"] == product.id
    assert payload["price_czk"] == 123.0
    assert captured["metadata"]["product_id"] == product.id

    def fake_list_templates():
        return [
            {
                "id": "tpl_test",
                "title": "Test produkt",
                "product_type": "bracelet",
                "price_czk": 123.0,
                "product_id": product.id,
                "created_at": "2026-02-04T00:00:00Z",
                "document": "doc",
            }
        ]

    monkeypatch.setattr(templates_service, "list_templates", fake_list_templates)

    res = client.get("/api/ai/templates/list")
    assert res.status_code == 200
    data = res.json()
    assert data["items"][0]["id"] == "tpl_test"


def test_ai_draft_price_null_when_no_templates(client, db_session, tmp_path, monkeypatch):
    upload_dir = Path(tmp_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = "draft_test.webp"
    (upload_dir / filename).write_bytes(b"fake-image")

    product = Product(
        name="Test produkt",
        description="Popis produktu",
        price_czk=150.0,
        stock=1,
        image=filename,
    )
    db_session.add(product)
    db_session.commit()

    monkeypatch.setattr(drafts_service, "suggest_price", lambda **kwargs: None)
    monkeypatch.setattr(
        drafts_service,
        "analyze_image_with_vision",
        lambda _: {"labels": ["bracelet", "bead"]},
    )

    res = client.post(f"/api/ai/products/{product.id}/draft")
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("suggested_price_czk") is None
