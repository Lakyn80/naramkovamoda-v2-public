from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import Payment, SoldProduct


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


def _to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    try:
        s = str(v).strip().replace(",", ".")
        return float(s) if s else 0.0
    except Exception:
        return 0.0


def _get_first_attr(obj: Any, *names: str) -> Any:
    for n in names:
        if hasattr(obj, n):
            val = getattr(obj, n)
            if val not in (None, ""):
                return val
    return None


def _sold_datetime(sp: SoldProduct) -> Optional[datetime]:
    return _get_first_attr(sp, "sold_at", "created_at")


def _to_row_dict(sp: SoldProduct) -> dict[str, Any]:
    sold_dt = _sold_datetime(sp)
    unit = _to_float(_get_first_attr(sp, "price", "unit_price_czk", "price_czk"))
    qty = max(1, int(_to_float(_get_first_attr(sp, "quantity", "qty"))))
    total = round(unit * qty, 2)
    order_id = None
    if getattr(sp, "payment_type", None) and str(sp.payment_type).startswith("order-"):
        try:
            order_id = int(str(sp.payment_type).replace("order-", ""))
        except Exception:
            pass
    vs = None
    if sp.note and "VS " in sp.note:
        for part in sp.note.split():
            if part.isdigit() and len(part) >= 4:
                vs = part
                break
    return {
        "id": sp.id,
        "order_id": order_id,
        "product_name": _get_first_attr(sp, "name", "product_name") or "Položka",
        "quantity": qty,
        "unit_price_czk": round(unit, 2),
        "total_czk": total,
        "status": getattr(sp, "status", None),
        "customer_email": _get_first_attr(sp, "customer_email", "email"),
        "vs": vs,
        "sold_at": sold_dt.isoformat() if sold_dt else None,
    }


def sold_list(db: Session, from_date: Optional[str], to_date: Optional[str]) -> tuple[list[dict], dict]:
    q = db.query(SoldProduct)
    d_from = _parse_date(from_date)
    d_to = _parse_date(to_date)
    if d_from:
        q = q.filter(SoldProduct.sold_at >= d_from)
    if d_to:
        q = q.filter(SoldProduct.sold_at < d_to + timedelta(days=1))
    q = q.order_by(SoldProduct.sold_at.desc(), SoldProduct.id.desc())
    items = q.all()
    rows = [_to_row_dict(sp) for sp in items]
    count = len(rows)
    total_amount = round(sum(_to_float(r.get("total_czk")) for r in rows), 2)
    summary = {"count": count, "total_amount": total_amount}
    return rows, summary
