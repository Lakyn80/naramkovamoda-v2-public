from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.models import SoldProduct
from app.db.session import get_db
from app.modules.auth.deps import require_admin
from app.modules.email.service import send_email
from app.modules.invoice.invoicing import build_invoice_pdf_bytes

from .service import sold_list

router = APIRouter(prefix="/api/sold", tags=["sold"], dependencies=[Depends(require_admin)])


@router.get("")
async def sold_list_endpoint(
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    rows, summary = sold_list(db, from_date, to_date)
    return {"rows": rows, "summary": summary}


@router.get("/export/xlsx")
async def sold_export_xlsx(
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    rows, _ = sold_list(db, from_date, to_date)
    try:
        import io
        from openpyxl import Workbook
    except ImportError:
        return Response(
            content='{"error": "openpyxl není nainstalován. pip install openpyxl"}',
            media_type="application/json",
            status_code=500,
        )
    wb = Workbook()
    ws = wb.active
    ws.title = "Prodané"
    headers = ["ID", "Objednávka", "Produkt", "Ks", "Cena/ks", "Celkem", "Email", "VS", "Datum"]
    ws.append(headers)
    for r in rows:
        ws.append([
            r.get("id"),
            r.get("order_id"),
            r.get("product_name", ""),
            r.get("quantity", 0),
            r.get("unit_price_czk", 0),
            r.get("total_czk", 0),
            r.get("customer_email") or "",
            r.get("vs") or "",
            r.get("sold_at", "")[:19] if r.get("sold_at") else "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"sold_{from_date or ''}_{to_date or ''}.xlsx".replace("__", "_").strip("_")
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/export/pdf")
async def sold_export_pdf(
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    rows, summary = sold_list(db, from_date, to_date)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        import io
    except ImportError:
        return Response(
            content='{"error": "reportlab není nainstalován"}',
            media_type="application/json",
            status_code=500,
        )
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 20 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, "Export prodaných")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Počet: {summary.get('count', 0)} | Celkem: {summary.get('total_amount', 0):.2f} CZK")
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "Produkt")
    c.drawRightString(120 * mm, y, "Ks")
    c.drawRightString(150 * mm, y, "Cena")
    c.drawRightString(180 * mm, y, "Celkem")
    y -= 5 * mm
    c.line(20 * mm, y, 180 * mm, y)
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    for r in rows[:50]:
        if y < 30 * mm:
            c.showPage()
            y = h - 20 * mm
        c.drawString(20 * mm, y, str(r.get("product_name", ""))[:40])
        c.drawRightString(120 * mm, y, str(r.get("quantity", "")))
        c.drawRightString(150 * mm, y, f"{r.get('unit_price_czk', 0):.2f}")
        c.drawRightString(180 * mm, y, f"{r.get('total_czk', 0):.2f}")
        y -= 5 * mm
    c.showPage()
    c.save()
    buf.seek(0)
    fn = f"sold_{from_date or ''}_{to_date or ''}.pdf".replace("__", "_").strip("_")
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'},
    )


@router.get("/{sold_id}/invoice-preview")
async def invoice_preview(
    sold_id: int,
    db: Session = Depends(get_db),
) -> Response:
    sp = db.query(SoldProduct).filter(SoldProduct.id == sold_id).first()
    if not sp:
        return Response(content="Not found", status_code=404)
    pdf_bytes = build_invoice_pdf_bytes(sp, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice_{sold_id}.pdf"'},
    )


@router.post("/{sold_id}/invoice-send")
async def invoice_send(
    sold_id: int,
    db: Session = Depends(get_db),
) -> dict:
    sp = db.query(SoldProduct).filter(SoldProduct.id == sold_id).first()
    if not sp:
        return {"ok": False, "error": "Prodaná položka nenalezena"}
    recipient = (getattr(sp, "customer_email", None) or "").strip()
    if not recipient:
        return {"ok": False, "error": "Chybí e-mail odběratele"}
    pdf_bytes = build_invoice_pdf_bytes(sp, db)
    send_email(
        subject=f"Faktura č. {sold_id}",
        recipients=[recipient],
        body="V příloze naleznete fakturu k objednávce.",
        attachments=[{"filename": f"invoice_{sold_id}.pdf", "content": pdf_bytes, "mimetype": "application/pdf"}],
    )
    return {"ok": True, "sent_to": recipient}
