from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(text: str) -> bool:
    token = BOT_TOKEN
    chat_id = CHAT_ID
    if not token or not chat_id:
        return False

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(api_url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read()
            obj = json.loads(body.decode("utf-8"))
            return bool(obj.get("ok"))
    except Exception:
        return False
