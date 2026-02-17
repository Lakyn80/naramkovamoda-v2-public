from __future__ import annotations

from app.db.models import Order, Payment, Product, SoldProduct


def test_delete_order_endpoint_removes_related_rows_and_restocks(client, db_session):
    product = Product(name="Test mazani", price_czk=199, stock=5)
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_resp = client.post(
        "/api/orders",
        json={
            "vs": "5550001",
            "name": "Test Zakaznik",
            "email": "test@example.com",
            "address": "Test 1",
            "items": [
                {
                    "id": product.id,
                    "name": product.name,
                    "quantity": 2,
                    "price": float(product.price_czk),
                }
            ],
        },
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["orderId"]

    order = db_session.get(Order, order_id)
    assert order is not None
    assert order.vs == "5550001"

    sold_row = SoldProduct(
        original_product_id=product.id,
        name=product.name,
        price="199.00",
        quantity=2,
        customer_name="Test Zakaznik",
        customer_email="test@example.com",
        customer_address="Test 1",
        payment_type=f"order-{order_id}",
    )
    db_session.add(sold_row)
    db_session.commit()

    delete_resp = client.delete(f"/api/payments/order/{order_id}")
    assert delete_resp.status_code == 200
    payload = delete_resp.json()
    assert payload["ok"] is True
    assert payload["orderId"] == order_id
    assert payload["deleted_order"] is True
    assert payload["deleted_payments"] >= 1
    assert payload["deleted_sold_rows"] >= 1
    assert payload["restocked_items"] == 1

    assert db_session.get(Order, order_id) is None
    assert db_session.query(Payment).filter(Payment.vs == "5550001").count() == 0
    assert db_session.query(SoldProduct).filter(SoldProduct.payment_type == f"order-{order_id}").count() == 0

    db_session.refresh(product)
    assert int(product.stock or 0) == 5
