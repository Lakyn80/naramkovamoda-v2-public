from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Order, OrderItem, SoldProduct
from app.modules.email.service import send_email
from app.modules.invoice.invoicing import build_invoice_pdf_bytes


def _to_dec(x) -> Decimal:
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal("0")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class _SoldProxy:
    id: int
    order_id: int
    created_at: datetime | None
    sold_at: datetime | None
    buyer_name: str | None
    email: str | None
    address: str | None
    note: str | None
    name: str
    quantity: float
    unit_price_czk: float
    total_czk: float
    vs: str | None
    items: list[dict[str, Any]] | None = None
    shipping_fee: float | None = None


def _sum_order_items(db: Session, order: Order) -> tuple[Decimal, int]:
    items: list[OrderItem] = db.query(OrderItem).filter_by(order_id=order.id).all()
    total = Decimal("0")
    count = 0
    for it in items:
        qty = _to_dec(it.quantity or 0)
        price = _to_dec(it.price or 0)
        total += qty * price
        count += int(qty)
    return total, count


def _shipping_fee_from_env() -> Decimal:
    raw = os.getenv("SHIPPING_FEE_CZK")
    if raw is None:
        raw = "89.00"
    try:
        return Decimal(str(raw))
    except Exception:
        return Decimal("89.00")


def _ensure_sold_rows(db: Session, order: Order) -> int:
    marker = f"order-{order.id}"
    try:
        existing_rows = db.query(SoldProduct).filter_by(payment_type=marker).all()
    except Exception:
        existing_rows = []

    existing_keys = {
        (
            (getattr(sp, "name", "") or "").strip().lower(),
            int(getattr(sp, "quantity", 0) or 0),
            str(_to_dec(getattr(sp, "price", 0))),
        )
        for sp in existing_rows
    }

    items: list[OrderItem] = db.query(OrderItem).filter_by(order_id=order.id).all()
    created = 0

    note_parts = [f"Objednávka #{order.id}"]
    if getattr(order, "vs", None):
        note_parts.append(f"VS {order.vs}")
    if getattr(order, "note", None):
        note_parts.append(str(order.note))
    base_note = " | ".join(note_parts)

    for it in items:
        key = (
            (getattr(it, "product_name", "") or "").strip().lower(),
            int(getattr(it, "quantity", 0) or 0),
            str(_to_dec(getattr(it, "price", 0))),
        )
        if key in existing_keys:
            continue

        price_dec = _to_dec(getattr(it, "price", 0))
        if price_dec < Decimal("1.00"):
            continue

        sp = SoldProduct(
            original_product_id=getattr(it, "product_id", None),
            name=getattr(it, "product_name", None) or getattr(it, "name", None) or "Položka",
            price=f"{price_dec:.2f}",
            quantity=int(getattr(it, "quantity", 1) or 1),
            customer_name=getattr(order, "customer_name", None),
            customer_email=getattr(order, "customer_email", None),
            customer_address=getattr(order, "customer_address", None),
            note=base_note,
            payment_type=marker,
            sold_at=datetime.utcnow(),
        )
        db.add(sp)
        created += 1

    if created:
        db.flush()
    return created


def _make_invoice_proxy(db: Session, order: Order) -> _SoldProxy:
    items_rows: list[OrderItem] = db.query(OrderItem).filter_by(order_id=order.id).all()
    items_payload: list[dict[str, Any]] = []
    subtotal = Decimal("0")
    for it in items_rows:
        qty = _to_dec(getattr(it, "quantity", 0) or 0)
        price = _to_dec(getattr(it, "price", 0) or 0)
        line_total = qty * price
        # Na fakturu jen skutečné položky (cena řádku >= 1 Kč; vyřadit 0,08 Kč a podobné)
        if line_total < Decimal("1.00"):
            continue
        subtotal += line_total
        items_payload.append(
            {
                "name": getattr(it, "product_name", None) or "Položka",
                "quantity": float(qty),
                "price": float(price),
            }
        )

    total_items, items_count = _sum_order_items(db, order)
    name = f"Objednávka #{order.id} – {items_count} položek"
    total_czk_val = _to_dec(getattr(order, "total_czk", None) or subtotal)
    if total_czk_val <= 0:
        total_czk_val = subtotal
    shipping_fee = total_czk_val - subtotal
    if shipping_fee < Decimal("0"):
        shipping_fee = _shipping_fee_from_env()

    # Když jsme vyřadili všechny položky (jen pod 1 Kč), jeden řádek = první produkt, částka bez poštovného
    if not items_payload and items_rows:
        default_shipping = _shipping_fee_from_env()
        subtotal = total_czk_val - default_shipping
        if subtotal < Decimal("0"):
            subtotal = total_czk_val
        first_it = items_rows[0]
        items_payload = [
            {
                "name": getattr(first_it, "product_name", None) or "Položka",
                "quantity": 1.0,
                "price": float(subtotal),
            }
        ]
        shipping_fee = float(default_shipping)
    return _SoldProxy(
        id=order.id,
        order_id=order.id,
        created_at=getattr(order, "created_at", None),
        sold_at=datetime.utcnow(),
        buyer_name=getattr(order, "customer_name", None),
        email=getattr(order, "customer_email", None),
        address=getattr(order, "customer_address", None),
        note=getattr(order, "note", None),
        name=name,
        quantity=1.0,
        unit_price_czk=float(subtotal),
        total_czk=float(total_czk_val),
        vs=getattr(order, "vs", None),
        items=items_payload,
        shipping_fee=float(shipping_fee),
    )


def _send_invoice_email(order: Order, pdf_bytes: bytes, filename: str) -> None:
    recipient = getattr(order, "customer_email", None)
    if not recipient:
        return

    subject = f"Faktura k objednávce #{order.id}"
    body = (
        f"Dobrý den {getattr(order, 'customer_name', '')},\n\n"
        "děkujeme za Vaši objednávku. V příloze posíláme fakturu (PDF).\n"
        "V případě nesrovnalostí odpovězte prosím na tento e-mail.\n\n"
        "Hezký den,\nNáramková Móda"
    )
    attachments = [{
        "filename": filename,
        "content": pdf_bytes,
        "mimetype": "application/pdf",
    }]
    send_email(subject=subject, recipients=[recipient], body=body, attachments=attachments)


def _send_admin_notification(order: Order, filename: str) -> None:
    admin_email = os.getenv("ORDER_NOTIFY_EMAIL")
    if not admin_email:
        return

    subject = f"Faktura odeslána – objednávka #{order.id}"
    body = (
        f"Objednávka #{order.id}\n"
        f"VS: {getattr(order, 'vs', None) or ''}\n"
        f"Zákazník: {getattr(order, 'customer_name', None) or ''} <{getattr(order, 'customer_email', None) or ''}>\n"
        f"Soubor: {filename}"
    )
    send_email(subject=subject, recipients=[admin_email], body=body)


def on_order_marked_paid(db: Session, order_id: int) -> dict:
    order: Order | None = db.get(Order, order_id)
    if not order:
        return {"ok": False, "error": "Order not found"}

    created_rows = _ensure_sold_rows(db, order)

    try:
        if created_rows:
            db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": f"DB commit failed: {exc}"}

    proxy = _make_invoice_proxy(db, order)
    pdf_bytes = build_invoice_pdf_bytes(proxy, db)
    filename = f"Invoice-Order-{order.id}.pdf"

    invoices_dir = Path(__file__).resolve().parents[4] / "static" / "invoices"
    _ensure_dir(invoices_dir)
    file_path = invoices_dir / filename

    already_sent = file_path.exists()
    if not already_sent:
        try:
            file_path.write_bytes(pdf_bytes)
        except Exception:
            pass

    emailed = False
    if not already_sent:
        try:
            _send_invoice_email(order, pdf_bytes, filename)
            emailed = True
        except Exception:
            pass

        try:
            _send_admin_notification(order, filename)
        except Exception:
            pass

    return {"ok": True, "sold_rows_created": created_rows, "emailed": emailed}
