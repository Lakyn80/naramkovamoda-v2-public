from __future__ import annotations

import os
import imaplib
import email
import re
import html as _html
from decimal import Decimal
from typing import Iterable, Optional

VS_RE = re.compile(r'(?:VS|Variabiln[íi]\s*symbol)\s*[:\-]?\s*(\d{1,10})', re.I)
AMT_RE = re.compile(r'(?:Částka|Castka)\s*[:\-]?\s*([+\-]?[\d\s]+[,.]\d{2})\s*(?:CZK|Kč)?', re.I)


def _parse_amount(text: str) -> Optional[Decimal]:
    m = AMT_RE.search(text or "")
    if not m:
        return None
    num = (m.group(1) or "").replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return Decimal(num)
    except Exception:
        return None


def _parse_vs(text: str) -> Optional[str]:
    m = VS_RE.search(text or "")
    return m.group(1) if m else None


def _sender_matches(addr: str, allow: Iterable[str]) -> bool:
    if not addr:
        return False
    addr_low = addr.lower()
    for pat in (allow or []):
        if pat.lower() in addr_low:
            return True
    return False


def _msg_to_text(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype.startswith("text/plain"):
                try:
                    body += part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8",
                        errors="ignore",
                    )
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8",
                errors="ignore",
            )
        except Exception:
            body = ""
    return body


def _msg_to_html(msg: email.message.Message) -> str:
    html = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if ctype.startswith("text/html"):
                try:
                    html += part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8",
                        errors="ignore",
                    )
                except Exception:
                    pass
    else:
        if (msg.get_content_type() or "").lower().startswith("text/html"):
            try:
                html = msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8",
                    errors="ignore",
                )
            except Exception:
                html = ""
    return html


def _extract_from_csob_html(html: str) -> tuple[Optional[str], Optional[Decimal]]:
    h = html or ""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = _html.unescape(h)
    h = re.sub(r"[ \t\u00A0]+", " ", h)

    m_vs = re.search(
        r"(?is)>\s*Variabiln[íi]\s*symbol\s*<\s*/\s*td\s*>\s*<\s*td[^>]*>\s*(\d{1,10})\s*<\s*/\s*td\s*>",
        h,
    )
    vs = m_vs.group(1) if m_vs else None

    m_amt = re.search(
        r"(?is)>\s*(?:Částka|Castka)\s*<\s*/\s*td\s*>\s*<\s*td[^>]*>\s*([+\-]?\d[\d\s]*[.,]\d{2})\s*(?:CZK|Kč)?\s*<\s*/\s*td\s*>",
        h,
    )
    amount = None
    if m_amt:
        num = m_amt.group(1).replace(" ", "").replace(",", ".")
        try:
            amount = Decimal(num)
        except Exception:
            amount = None

    return vs, amount


def fetch_from_imap(
    *,
    host: str,
    port: int,
    ssl: bool,
    user: str,
    password: str,
    folder: str = "INBOX",
    max_items: int = 50,
    allow_senders: Optional[Iterable[str]] = None,
    mark_seen: bool = True,
) -> list[tuple[str, Decimal, str]]:
    imap = imaplib.IMAP4_SSL(host, port) if ssl else imaplib.IMAP4(host, port)
    imap.login(user, password)
    imap.select(folder)

    typ, data = imap.search(None, "(UNSEEN)")
    ids = data[0].split()
    if not ids:
        imap.close()
        imap.logout()
        return []

    out: list[tuple[str, Decimal, str]] = []

    for msg_id in reversed(ids):
        if len(out) >= max_items:
            break

        typ, data = imap.fetch(msg_id, "(RFC822)")
        if typ != "OK":
            continue

        raw = data[0][1]
        msg = email.message_from_bytes(raw)
        sender_hdr = ((msg.get("From") or "") + " " + (msg.get("Sender") or "")).strip()
        subject = (msg.get("Subject") or "")

        if allow_senders and not _sender_matches(sender_hdr, allow_senders):
            continue

        html_text = _msg_to_html(msg)
        body_text = _msg_to_text(msg)

        vs, amt = (None, None)
        if html_text:
            vs, amt = _extract_from_csob_html(html_text)
        if not vs:
            vs = _parse_vs(body_text) or _parse_vs(subject)
        if amt is None:
            amt = _parse_amount(body_text)

        if vs and amt is not None:
            out.append((vs, amt, sender_hdr))
            if mark_seen:
                try:
                    imap.store(msg_id, "+FLAGS", r"\Seen")
                except Exception:
                    pass

    imap.close()
    imap.logout()
    return out


def fetch_csob_incoming(
    host: Optional[str] = None,
    port: Optional[int] = None,
    ssl: Optional[bool] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    folder: Optional[str] = None,
    max_items: int = 50,
    bank_senders: Optional[Iterable[str]] = None,
    mark_seen: bool = True,
) -> list[tuple[str, Decimal]]:
    host = host or os.getenv("IMAP_HOST", "imap.seznam.cz")
    port = int(port or os.getenv("IMAP_PORT", "993"))
    ssl = (ssl if ssl is not None else os.getenv("IMAP_SSL", "true").lower() == "true")
    user = user or os.getenv("IMAP_USER")
    password = password or os.getenv("IMAP_PASSWORD")
    folder = folder or os.getenv("IMAP_FOLDER", "INBOX")

    if not (user and password):
        raise RuntimeError("Chybí IMAP_USER/IMAP_PASSWORD v .env nebo parametrech.")

    bank_senders = list(bank_senders) if bank_senders else [
        "csob.cz", "noreply@csob.cz", "no-reply@csob.cz", "notification@csob.cz", "info@csob.cz"
    ]

    rows = fetch_from_imap(
        host=host,
        port=port,
        ssl=ssl,
        user=user,
        password=password,
        folder=folder,
        max_items=max_items,
        allow_senders=bank_senders,
        mark_seen=mark_seen,
    )
    return [(vs, amt) for (vs, amt, _sender) in rows]
