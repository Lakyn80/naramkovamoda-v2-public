from __future__ import annotations

from app.db.models import Product
from app.modules.orders import service as orders_service


def test_order_emails_sent_with_qr(client, db_session, monkeypatch):
    monkeypatch.setenv("ORDER_NOTIFY_EMAIL", "admin@example.com")

    calls = []

    def fake_send_email(subject, recipients, body, attachments=None, sender=None):
        calls.append(
            {
                "subject": subject,
                "recipients": list(recipients or []),
                "body": body,
                "attachments": attachments,
            }
        )
        return None

    monkeypatch.setattr(orders_service, "send_email", fake_send_email)
    monkeypatch.setattr(orders_service, "payment_qr_png", lambda *args, **kwargs: (200, b"qr", {}))

    product = Product(name="Test produkt", price_czk=199, stock=5)
    db_session.add(product)
    db_session.commit()

    payload = {
        "vs": "123456",
        "name": "Test zákazník",
        "email": "customer@example.com",
        "address": "Test adresa 1",
        "items": [
            {
                "id": product.id,
                "name": product.name,
                "quantity": 1,
                "price": float(product.price_czk),
            }
        ],
    }

    res = client.post("/api/orders", json=payload)
    assert res.status_code == 201

    assert len(calls) == 2
    customer_call = next(c for c in calls if "customer@example.com" in c["recipients"])
    admin_call = next(c for c in calls if "admin@example.com" in c["recipients"])

    assert "Potvrzení objednávky" in (customer_call["subject"] or "")
    assert customer_call["attachments"] is not None
    assert customer_call["attachments"][0]["filename"] == "qr-platba.png"

    assert "Nová objednávka" in (admin_call["subject"] or "")
    assert not admin_call["attachments"]
