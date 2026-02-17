from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val in (None, "", "None"):
        return default
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on")


def send_email(subject, recipients, body, attachments=None, sender=None, html_body=None):
    """
    Odeslání textového e-mailu v UTF-8 s volitelnými přílohami.
    """
    if isinstance(recipients, str):
        recipients = [recipients]

    recipients = list(recipients or [])
    if not recipients:
        return None

    mail_server = os.getenv("MAIL_SERVER", "smtp.seznam.cz")
    mail_port = int(os.getenv("MAIL_PORT", "465"))
    mail_user = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_default_sender = os.getenv("MAIL_DEFAULT_SENDER") or mail_user

    if _env_bool("MAIL_SUPPRESS_SEND", False):
        return None

    msg = EmailMessage()
    msg["Subject"] = subject or ""
    msg["From"] = sender or mail_default_sender or ""
    msg["To"] = ", ".join(recipients)
    msg.set_content(body or "", subtype="plain", charset="utf-8")
    if html_body:
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

    for att in attachments or []:
        if not isinstance(att, dict):
            continue
        filename = att.get("filename") or "attachment"
        data = att.get("content", att.get("data"))
        mimetype = att.get("mimetype") or att.get("content_type") or "application/octet-stream"
        if data is None:
            continue
        maintype, subtype = mimetype.split("/", 1) if "/" in mimetype else (mimetype, "octet-stream")
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    use_ssl = _env_bool("MAIL_USE_SSL", True)
    use_tls = _env_bool("MAIL_USE_TLS", False)

    if use_ssl:
        server = smtplib.SMTP_SSL(mail_server, mail_port)
    else:
        server = smtplib.SMTP(mail_server, mail_port)

    try:
        if use_tls and not use_ssl:
            server.starttls()
        if mail_user and mail_password:
            server.login(mail_user, mail_password)
        server.send_message(msg)
    finally:
        server.quit()

    return msg
