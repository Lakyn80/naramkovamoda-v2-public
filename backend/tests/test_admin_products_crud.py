from __future__ import annotations

import io

from app.db.models import Category, Product, ProductVariant


def _create_category(db_session):
    cat = Category(name="Test", slug="test", group="Skupina")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def test_create_product(client, db_session):
    cat = _create_category(db_session)
    data = {
        "name": "Produkt A",
        "description": "Popis",
        "price_czk": "199",
        "stock": "3",
        "category_id": str(cat.id),
    }
    files = {
        "image": ("test.jpg", io.BytesIO(b"fake"), "image/jpeg")
    }
    response = client.post("/api/products/", data=data, files=files)
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Produkt A"
    assert payload["price"] == 199.0


def test_update_product(client, db_session):
    cat = _create_category(db_session)
    create = client.post(
        "/api/products/",
        data={
            "name": "Produkt B",
            "price": "149",
            "stock": "1",
            "category_id": str(cat.id),
        },
    )
    product_id = create.json()["id"]

    response = client.put(f"/api/products/{product_id}", json={"name": "Produkt C"})
    assert response.status_code == 200
    assert response.json()["name"] == "Produkt C"


def test_delete_product(client, db_session):
    cat = _create_category(db_session)
    create = client.post(
        "/api/products/",
        data={
            "name": "Produkt D",
            "price": "99",
            "stock": "1",
            "category_id": str(cat.id),
        },
    )
    product_id = create.json()["id"]

    response = client.delete(f"/api/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Deleted"

    get_resp = client.get(f"/api/products/{product_id}")
    assert get_resp.status_code == 404


def test_update_product_without_variants_does_not_delete_existing_variants(client, db_session):
    cat = _create_category(db_session)
    product = Product(
        name="Produkt Variant",
        price_czk=149,
        stock=1,
        category_id=cat.id,
    )
    db_session.add(product)
    db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        variant_name="18 cm",
        stock=2,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(product)

    response = client.put(f"/api/products/{product.id}", json={"active": False})
    assert response.status_code == 200

    variants = db_session.query(ProductVariant).filter_by(product_id=product.id).all()
    assert len(variants) == 1
    assert variants[0].variant_name == "18 cm"


def test_create_product_auto_price_for_bracelet_category(client, db_session):
    cat = Category(name="Náramky", slug="naramky", group="Skupina")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    response = client.post(
        "/api/products/",
        json={
            "name": "Test náramek",
            "description": "Bez přívěsku",
            "stock": 1,
            "category_id": cat.id,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["price"] == 149.0


def test_create_product_auto_variant_price_for_bracelet(client, db_session):
    cat = Category(name="Náramky", slug="naramky", group="Skupina")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    response = client.post(
        "/api/products/",
        json={
            "name": "Základní náramek",
            "description": "Model s přívěškem",
            "category_id": cat.id,
            "variants": [
                {
                    "variant_name": "Varianta s přívěškem",
                    "description": "s přívěškem",
                    "stock": 1,
                },
                {
                    "variant_name": "Varianta bez přívěsku",
                    "description": "bez přívěsku",
                    "stock": 1,
                },
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["price"] == 159.0
    assert len(payload["variants"]) == 2
    prices = [v.get("price_czk") for v in payload["variants"]]
    assert 159.0 in prices
    assert 149.0 in prices
