from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

SESSION_COOKIE = "admin_session"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def session_ttl_seconds() -> int:
    raw = os.getenv("ADMIN_SESSION_TTL_HOURS", "72")
    try:
        hours = int(raw)
        return max(hours, 1) * 3600
    except Exception:
        return 72 * 3600


def session_secret() -> bytes:
    secret = (
        os.getenv("ADMIN_SESSION_SECRET")
        or os.getenv("PASSWORD_RESET_SALT")
        or "dev-secret"
    )
    return secret.encode("utf-8")


def make_session_token(user_id: int) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + session_ttl_seconds()}
    payload_b = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(session_secret(), payload_b.encode("utf-8"), hashlib.sha256).digest()
    sig_b = _b64url_encode(signature)
    return f"{payload_b}.{sig_b}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    payload_b, sig_b = token.split(".", 1)
    try:
        payload_raw = _b64url_decode(payload_b)
        provided_sig = _b64url_decode(sig_b)
    except Exception:
        return None
    expected_sig = hmac.new(session_secret(), payload_b.encode("utf-8"), hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None
    try:
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()):
        return None
    return payload
