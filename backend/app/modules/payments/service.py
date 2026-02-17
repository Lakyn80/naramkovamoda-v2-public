from __future__ import annotations

import io
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import qrcode
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import Order, OrderItem, Payment, Product, SoldProduct
from app.modules.orders.order_paid_hook import on_order_marked_paid
from .csob_mail_sync import fetch_csob_incoming, fetch_from_imap
from .telegram import send_telegram_message


# --- Helpers ---------------------------------------------------------------

def _get_iban() -> str:
    iban = os.getenv("MERCHANT_IBAN")
    if not iban:
        raise RuntimeError("MERCHANT_IBAN není nastaven (ENV nebo Config).")
    return iban.replace(" ", "").upper()


def _to_decimal(val) -> Decimal:
    return Decimal(str(val))


def _build_spd_payload(iban: str, amount: Decimal, vs: str | None, msg: str | None) -> str:
    """SPD 1.0 – ČBA formát pro QR platby v CZK (qr-platba.cz)."""
    iban_clean = iban.replace(" ", "").upper().strip()
    if not iban_clean or len(iban_clean) < 15:
        raise ValueError("IBAN musí být platné české číslo účtu (CZ + 22 číslic).")
    parts = [
        "SPD*1.0",
        f"ACC:{iban_clean}",
        f"AM:{float(amount):.2f}",
        "CC:CZK",
    ]
    if vs:
        vs_clean = "".join(c for c in str(vs).strip() if c.isdigit())[:10]
        if vs_clean:
            parts.append(f"X-VS:{vs_clean}")
    if msg:
        safe_msg = "".join(ch for ch in (msg or "") if 32 <= ord(ch) <= 126)[:60]
        if safe_msg:
            parts.append(f"MSG:{safe_msg}")
    return "*".join(parts)


def _safe_int(value, default):
    try:
        v = int(value)
        return v if v >= 0 else default
    except Exception:
        return default


def _normalize_order_status(value: str | None) -> str | None:
    raw = (value or "").strip().lower()
    if raw in ("paid", "zaplaceno", "zaplacení", "zaplaceny", "zaplacena"):
        return "paid"
    if raw in ("awaiting_payment", "pending", "cekam", "cekani", "cekam_na_platbu", "cekání", "čeká", "čeká na platbu"):
        return "awaiting_payment"
    if raw in ("canceled", "cancelled", "zruseno", "zrušeno", "storno", "cancel"):
        return "canceled"
    return None


def _detect_order_item_schema(db: Session) -> dict[str, Any]:
    cols = db.execute(text("PRAGMA table_info('order_item');")).fetchall()
    colnames = {c[1] for c in cols}

    price_cols = [c for c in ("price_czk", "unit_price_czk", "unit_price") if c in colnames]
    qty_cols = [c for c in ("quantity", "qty", "count") if c in colnames]
    amount_cols = [c for c in ("amount_czk",) if c in colnames]

    fk_col = "order_id" if "order_id" in colnames else None

    return {
        "has_table": len(cols) > 0,
        "price_cols": price_cols,
        "qty_cols": qty_cols,
        "amount_cols": amount_cols,
        "fk_col": fk_col,
    }


def _compute_amounts_for_orders(db: Session, order_ids: list[int]) -> dict[int, float]:
    if not order_ids:
        return {}

    schema = _detect_order_item_schema(db)
    if not schema["has_table"] or not schema["fk_col"]:
        return {}

    fk = schema["fk_col"]
    if schema["amount_cols"]:
        amount_col = schema["amount_cols"][0]
        sql = f"""
            SELECT {fk} as oid, COALESCE(SUM({amount_col}), 0) AS total
            FROM order_item
            WHERE {fk} IN :ids
            GROUP BY {fk}
        """
        rows = db.execute(text(sql.replace(":ids", "(:ids)")), {"ids": tuple(order_ids)}).fetchall()
        return {r.oid: float(r.total) for r in rows}

    if schema["price_cols"] and schema["qty_cols"]:
        price = schema["price_cols"][0]
        qty = schema["qty_cols"][0]
        sql = f"""
            SELECT {fk} as oid, COALESCE(SUM({price} * {qty}), 0) AS total
            FROM order_item
            WHERE {fk} IN :ids
            GROUP BY {fk}
        """
        rows = db.execute(text(sql.replace(":ids", "(:ids)")), {"ids": tuple(order_ids)}).fetchall()
        return {r.oid: float(r.total) for r in rows}

    return {}


def _vs_display(vs, order_id):
    vs = (vs or "").strip()
    return vs if vs else f"{int(order_id):08d}"


def _shipping_fee() -> Decimal:
    raw = os.getenv("SHIPPING_FEE_CZK")
    if raw is None:
        raw = "89.00"
    try:
        return _to_decimal(raw)
    except InvalidOperation:
        return Decimal("89.00")


def _amounts_equal(a: Decimal, b: Decimal, tol: Decimal = Decimal("0.50")) -> bool:
    return abs(_to_decimal(a) - _to_decimal(b)) <= _to_decimal(tol)


def _order_base_amount_czk(db: Session, order: Order) -> Decimal | None:
    total = getattr(order, "total_czk", None)
    if total is not None:
        try:
            return _to_decimal(total)
        except InvalidOperation:
            return None

    comp = _compute_amounts_for_orders(db, [order.id])
    if comp.get(order.id) is not None:
        try:
            return _to_decimal(comp[order.id])
        except InvalidOperation:
            return None
    return None


# --- QR endpoints ----------------------------------------------------------

def payment_qr_png(amount_raw: str | None, vs: str | None, msg: str | None) -> tuple[int, dict[str, Any] | bytes, dict[str, str]]:
    try:
        amount_raw = (amount_raw or "").strip()
        if not amount_raw:
            return 400, {"ok": False, "error": "Chybí query param 'amount'."}, {}

        try:
            amount = _to_decimal(amount_raw)
        except InvalidOperation:
            return 400, {"ok": False, "error": "Neplatná částka 'amount'."}, {}
        if amount <= 0:
            return 400, {"ok": False, "error": "Částka musí být > 0."}, {}

        vs_val = (vs or "").strip() or None
        msg_val = (msg or "").strip() or None

        iban = _get_iban()
        payload = _build_spd_payload(iban, amount, vs_val, msg_val)

        img = qrcode.make(payload)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        headers = {
            "Cache-Control": "public, max-age=60",
            "Content-Disposition": "inline; filename=qr-platba.png",
        }
        return 200, buf.read(), headers
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}, {}


def payment_qr_payload(amount_raw: str | None, vs: str | None, msg: str | None) -> tuple[int, dict[str, Any]]:
    try:
        amount_raw = (amount_raw or "").strip()
        if not amount_raw:
            return 400, {"ok": False, "error": "Chybí query param 'amount'."}
        try:
            amount = _to_decimal(amount_raw)
        except InvalidOperation:
            return 400, {"ok": False, "error": "Neplatná částka 'amount'."}
        if amount <= 0:
            return 400, {"ok": False, "error": "Částka musí být > 0."}

        vs_val = (vs or "").strip() or None
        msg_val = (msg or "").strip() or None

        iban = _get_iban()
        payload = _build_spd_payload(iban, amount, vs_val, msg_val)
        return 200, {"ok": True, "iban": iban, "amount": float(amount), "payload": payload}
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


# --- Summary/list ----------------------------------------------------------

def payments_summary(db: Session) -> tuple[int, dict[str, Any]]:
    try:
        total = db.query(Order).count()
        items = db.query(Order).order_by(Order.id.desc()).limit(5).all()
        ids = [o.id for o in items]
        computed = _compute_amounts_for_orders(db, ids) if ids else {}

        def map_order(o: Order):
            vs_out = _vs_display(getattr(o, "vs", None), o.id)
            total_czk = getattr(o, "total_czk", None)
            amount_val = (float(total_czk) if total_czk is not None else computed.get(o.id))
            created_at = getattr(o, "created_at", None)
            return {
                "id": o.id,
                "vs": vs_out,
                "status": getattr(o, "status", None),
                "amount": amount_val,
                "received_at": (created_at.isoformat() if created_at else None),
            }

        sample = [map_order(o) for o in items]

        columns_present = []
        for attr in ("id", "vs", "status", "total_czk", "created_at"):
            columns_present.append(attr if hasattr(Order, attr) else f"!missing:{attr}")

        return 200, {
            "ok": True,
            "source_table": "Order",
            "count": total,
            "sample": sample,
            "columns_present": columns_present,
        }
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def payments_list(db: Session, params: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        page = _safe_int(params.get("page", 1), 1)
        per_page = min(max(_safe_int(params.get("per_page", 20), 20), 1), 200)
        status = (params.get("status") or "").strip() or None
        sort = (params.get("sort") or "id").strip()
        direction = (params.get("direction") or "desc").strip().lower()
        if direction not in ("asc", "desc"):
            direction = "desc"

        q = db.query(Order)
        if status and hasattr(Order, "status"):
            q = q.filter(Order.status == status)

        sort_map = {
            "id": getattr(Order, "id", None),
            "vs": getattr(Order, "vs", None),
            "status": getattr(Order, "status", None),
            "amount": getattr(Order, "total_czk", None),
            "total_czk": getattr(Order, "total_czk", None),
            "received_at": getattr(Order, "created_at", None),
            "created_at": getattr(Order, "created_at", None),
        }
        sort_col = sort_map.get(sort) or sort_map["id"]
        q = q.order_by(sort_col.asc() if direction == "asc" else sort_col.desc())

        total = q.count()
        items = q.limit(per_page).offset((page - 1) * per_page).all()
        ids = [o.id for o in items]
        computed = _compute_amounts_for_orders(db, ids) if ids else {}

        def map_order(o: Order):
            vs_out = _vs_display(getattr(o, "vs", None), o.id)
            total_czk = getattr(o, "total_czk", None)
            amount_val = (float(total_czk) if total_czk is not None else computed.get(o.id))
            created_at = getattr(o, "created_at", None)
            return {
                "id": o.id,
                "vs": vs_out,
                "status": getattr(o, "status", None),
                "amount": amount_val,
                "received_at": (created_at.isoformat() if created_at else None),
            }

        items_out = [map_order(o) for o in items]

        return 200, {
            "ok": True,
            "source_table": "Order",
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": items_out,
            "sort": {"column": sort, "direction": direction},
        }
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


# --- Payments / pairing -----------------------------------------------------

def mark_paid_by_vs(db: Session, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        vs = str(payload.get("vs", "")).strip()
        if not vs:
            return 400, {"ok": False, "error": "Chybí VS."}

        amount = None
        amount_in = payload.get("amountCzk", None)
        if amount_in is not None and str(amount_in).strip() != "":
            try:
                amount = _to_decimal(amount_in)
                if amount < 0:
                    return 400, {"ok": False, "error": "Částka nesmí být záporná."}
            except InvalidOperation:
                return 400, {"ok": False, "error": "Neplatná částka 'amountCzk'."}

        ref = str(payload.get("reference", "") or "").strip()
        if len(ref) > 255:
            ref = ref[:255]

        pay = db.query(Payment).filter_by(vs=vs).order_by(Payment.id.desc()).first()

        if pay:
            pay.status = "received"
            if amount is not None:
                setattr(pay, "amount_czk", amount)
            if ref:
                pay.reference = (f"{pay.reference} | {ref}" if pay.reference else ref)
            if getattr(pay, "received_at", None) is None:
                pay.received_at = datetime.utcnow()
            created = False
        else:
            pay = Payment(
                vs=vs,
                status="received",
                amount_czk=(amount if amount is not None else None),
                reference=(ref or None),
                received_at=datetime.utcnow(),
            )
            db.add(pay)
            created = True

        order = db.query(Order).filter_by(vs=vs).first()
        if order:
            order.status = "paid"

        db.commit()

        return (201 if created else 200), {
            "ok": True,
            "created": created,
            "paymentId": pay.id,
            "orderId": (order.id if order else None),
            "status": "received",
        }

    except Exception as e:
        db.rollback()
        return 500, {"ok": False, "error": str(e)}


def update_payment_status(db: Session, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        order_id = payload.get("order_id") or payload.get("payment_id") or payload.get("id")
        vs = (payload.get("vs") or "").strip()
        status_raw = payload.get("status")
        status_norm = _normalize_order_status(status_raw)

        if not status_norm:
            return 400, {"ok": False, "error": "Neplatný status."}

        order = None
        if order_id is not None:
            try:
                order = db.get(Order, int(order_id))
            except Exception:
                order = None

        if not order and vs:
            order = db.query(Order).filter_by(vs=vs).first()

        if not order:
            return 404, {"ok": False, "error": "Objednávka nenalezena."}

        order.status = status_norm

        pay = None
        if getattr(order, "vs", None):
            pay = db.query(Payment).filter_by(vs=str(order.vs)).order_by(Payment.id.desc()).first()

        if pay:
            if status_norm == "paid":
                pay.status = "received"
                if getattr(pay, "received_at", None) is None:
                    pay.received_at = datetime.utcnow()
            elif status_norm == "awaiting_payment":
                pay.status = "pending"
            elif status_norm == "canceled":
                pay.status = "canceled"

        db.commit()

        hook_result = None
        if status_norm == "paid":
            hook_result = on_order_marked_paid(db, order.id)

        return 200, {
            "ok": True,
            "orderId": order.id,
            "status": status_norm,
            "sold_rows_created": (hook_result or {}).get("sold_rows_created"),
            "emailed": (hook_result or {}).get("emailed"),
        }

    except Exception as e:
        db.rollback()
        return 500, {"ok": False, "error": str(e)}


def delete_order_with_relations(db: Session, order_id: int) -> tuple[int, dict[str, Any]]:
    try:
        order = db.get(Order, int(order_id))
        if not order:
            return 404, {"ok": False, "error": "Objednávka nenalezena."}

        order_items = db.query(OrderItem).filter_by(order_id=order.id).all()
        restocked_items = 0
        for item in order_items:
            name = (getattr(item, "product_name", None) or "").strip()
            qty = int(getattr(item, "quantity", 0) or 0)
            if not name or qty <= 0:
                continue
            candidates = db.query(Product).filter(Product.name == name).all()
            if len(candidates) == 1:
                product = candidates[0]
                product.stock = int(product.stock or 0) + qty
                if hasattr(product, "active") and int(product.stock or 0) > 0:
                    product.active = True
                restocked_items += 1

        vs = (getattr(order, "vs", None) or "").strip()
        deleted_payments = 0
        if vs:
            deleted_payments = db.query(Payment).filter(Payment.vs == vs).delete(synchronize_session=False)

        deleted_sold_rows = db.query(SoldProduct).filter(
            SoldProduct.payment_type == f"order-{order.id}"
        ).delete(synchronize_session=False)

        db.delete(order)
        db.commit()

        return 200, {
            "ok": True,
            "orderId": order_id,
            "deleted_order": True,
            "deleted_payments": int(deleted_payments or 0),
            "deleted_sold_rows": int(deleted_sold_rows or 0),
            "restocked_items": restocked_items,
        }
    except Exception as e:
        db.rollback()
        return 500, {"ok": False, "error": str(e)}


def sync_from_orders(db: Session) -> tuple[int, dict[str, Any]]:
    try:
        created = 0
        q = (
            db.query(Order)
            .outerjoin(Payment, Payment.vs == Order.vs)
            .filter(
                Order.status == "awaiting_payment",
                Order.vs.isnot(None),
                Order.vs != "",
                Order.total_czk.isnot(None),
                Payment.id.is_(None),
            )
        )
        for o in q.all():
            db.add(
                Payment(
                    vs=o.vs,
                    amount_czk=o.total_czk,
                    status="pending",
                    reference=f"auto-sync order #{o.id}",
                )
            )
            created += 1

        if created:
            db.commit()

        return 200, {"ok": True, "created": created}
    except Exception as e:
        db.rollback()
        return 500, {"ok": False, "error": str(e)}


def get_status_by_vs(db: Session, vs: str) -> tuple[int, dict[str, Any]]:
    try:
        vs_val = (vs or "").strip()
        if not vs_val:
            return 400, {"ok": False, "error": "Chybí VS."}

        pay = db.query(Payment).filter_by(vs=vs_val).order_by(Payment.id.desc()).first()
        order = db.query(Order).filter_by(vs=vs_val).first()

        return 200, {
            "ok": True,
            "payment": None if not pay else {
                "id": pay.id,
                "vs": pay.vs,
                "amountCzk": (float(getattr(pay, "amount_czk")) if getattr(pay, "amount_czk", None) is not None else None),
                "status": pay.status,
                "reference": getattr(pay, "reference", None),
                "received_at": (pay.received_at.isoformat() if getattr(pay, "received_at", None) else None),
            },
            "order": None if not order else {
                "id": order.id,
                "status": getattr(order, "status", None),
                "totalCzk": (float(getattr(order, "total_czk")) if getattr(order, "total_czk", None) is not None else None),
                "created_at": (order.created_at.isoformat() if getattr(order, "created_at", None) else None),
            },
        }

    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def sync_csob_mail(db: Session, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        cfg = payload or {}
        host = cfg.get("host")
        port = cfg.get("port")
        ssl = cfg.get("ssl")
        user = cfg.get("user")
        password = cfg.get("password")
        folder = cfg.get("folder") or "INBOX"
        max_ = cfg.get("max", 50)

        bank_senders = cfg.get("bank_senders") or [
            "csob.cz", "noreply@csob.cz", "no-reply@csob.cz", "notification@csob.cz", "info@csob.cz"
        ]
        self_senders = cfg.get("self_senders") or [
            "noreply@naramkovamoda.cz", "naramkovamoda@email.cz"
        ]

        bank_pairs = fetch_csob_incoming(
            host=host,
            port=port,
            ssl=ssl,
            user=user,
            password=password,
            folder=folder,
            max_items=max_,
            bank_senders=bank_senders,
            mark_seen=True,
        )

        processed: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        fee = _shipping_fee()

        for vs_val, amount in bank_pairs:
            order = db.query(Order).filter_by(vs=str(vs_val)).first()
            if not order:
                unmatched.append({
                    "vs": str(vs_val),
                    "reason": "order_not_found",
                    "paid": float(amount),
                })
                continue

            expected_dec = None
            total_czk_val = getattr(order, "total_czk", None)
            if total_czk_val is not None:
                try:
                    expected_dec = _to_decimal(total_czk_val)
                except InvalidOperation:
                    expected_dec = None

            if expected_dec is None:
                base = _order_base_amount_czk(db, order)
                if base is None:
                    unmatched.append({
                        "vs": str(vs_val),
                        "reason": "order_amount_missing",
                        "paid": float(amount),
                    })
                    continue
                expected_dec = _to_decimal(base) + fee

            paid_dec = _to_decimal(amount)

            if _amounts_equal(paid_dec, expected_dec):
                if order.status != "paid":
                    order.status = "paid"

                pay = db.query(Payment).filter_by(vs=str(vs_val)).order_by(Payment.id.desc()).first()
                if pay:
                    pay.status = "received"
                    pay.amount_czk = paid_dec
                    if getattr(pay, "received_at", None) is None:
                        pay.received_at = datetime.utcnow()
                else:
                    pay = Payment(vs=str(vs_val), amount_czk=paid_dec, status="received", received_at=datetime.utcnow())
                    db.add(pay)

                processed.append({
                    "vs": str(vs_val),
                    "amount": float(paid_dec),
                    "expected": float(expected_dec),
                    "orderId": order.id,
                })
            else:
                unmatched.append({
                    "vs": str(vs_val),
                    "reason": "amount_mismatch",
                    "paid": float(paid_dec),
                    "expected": float(expected_dec),
                    "orderId": order.id,
                })

        if processed:
            db.commit()
            lines = [
                f"✅ Přijata platba VS {p['vs']} • {p['amount']:.2f} CZK (oček. {p['expected']:.2f}) • objednávka #{p['orderId']}"
                for p in processed
            ]
            try:
                send_telegram_message("\n".join(lines))
            except Exception:
                pass

        try:
            self_rows = fetch_from_imap(
                host=host or os.getenv("IMAP_HOST", "imap.seznam.cz"),
                port=int(port or os.getenv("IMAP_PORT", "993")),
                ssl=(ssl if ssl is not None else os.getenv("IMAP_SSL", "true").lower() == "true"),
                user=user or os.getenv("IMAP_USER"),
                password=password or os.getenv("IMAP_PASSWORD"),
                folder=folder,
                max_items=max_,
                allow_senders=self_senders,
                mark_seen=True,
            )
            diagnostic_self = [
                {"vs": vs, "amount": float(amount), "sender": sender}
                for (vs, amount, sender) in self_rows
            ]
        except Exception:
            diagnostic_self = []

        return 200, {
            "ok": True,
            "shipping_fee_czk": float(fee),
            "matched": processed,
            "unmatched": unmatched,
            "diagnostic_self": diagnostic_self,
        }

    except Exception as e:
        db.rollback()
        return 500, {"ok": False, "error": str(e)}
