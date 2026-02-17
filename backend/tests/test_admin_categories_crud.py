from __future__ import annotations

from app.db.models import Category, Product


def test_create_category(client):
    response = client.post("/api/categories/", json={"name": "Kategorie A"})
    assert response.status_code == 201
    assert response.json()["name"] == "Kategorie A"


def test_update_category(client):
    created = client.post("/api/categories/", json={"name": "Kategorie B"})
    category_id = created.json()["id"]

    response = client.put(f"/api/categories/{category_id}", json={"name": "Kategorie C"})
    assert response.status_code == 200
    assert response.json()["name"] == "Kategorie C"


def test_delete_category_with_products_requires_force(client, db_session):
    category = Category(name="Kategorie D", slug="kategorie-d")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    product = Product(
        name="Produkt E",
        price_czk=10,
        stock=1,
        category_id=category.id,
    )
    db_session.add(product)
    db_session.commit()

    response = client.delete(f"/api/categories/{category.id}")
    assert response.status_code == 400
    assert "Kategorie obsahuje produkty" in response.json()["detail"]

    response_force = client.delete(f"/api/categories/{category.id}?force=true")
    assert response_force.status_code == 200
    assert response_force.json()["ok"] is True

