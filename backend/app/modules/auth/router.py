from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.modules.email.service import send_email

from .deps import require_admin
from .session import SESSION_COOKIE, make_session_token, session_ttl_seconds

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _password_context():
    from passlib.context import CryptContext

    # Keep bcrypt/plaintext compatibility for existing records,
    # hash new passwords with pbkdf2_sha256 to avoid bcrypt 72-byte limit.
    return CryptContext(schemes=["pbkdf2_sha256", "bcrypt", "plaintext"], deprecated="auto")


def _check_password(hashed: str, plain: str) -> bool:
    try:
        ctx = _password_context()
        return ctx.verify(plain, hashed)
    except Exception:
        pass
    try:
        from werkzeug.security import check_password_hash
        return check_password_hash(hashed, plain)
    except Exception:
        return False


def _hash_password(plain: str) -> str:
    from passlib.hash import pbkdf2_sha256

    return pbkdf2_sha256.hash(plain)


def _reset_secret() -> bytes | None:
    salt = os.getenv("PASSWORD_RESET_SALT")
    if not salt:
        return None
    return salt.encode("utf-8")


def _token_ttl_seconds() -> int:
    raw = os.getenv("PASSWORD_RESET_TTL_HOURS", "24")
    try:
        hours = int(raw)
        return max(hours, 1) * 3600
    except Exception:
        return 24 * 3600


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _make_reset_token(user: User) -> str:
    secret = _reset_secret()
    if not secret:
        raise RuntimeError("PASSWORD_RESET_SALT není nastaven.")
    payload = {
        "uid": user.id,
        "email": user.email,
        "exp": int(time.time()) + _token_ttl_seconds(),
    }
    payload_b = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(secret, payload_b.encode("utf-8"), hashlib.sha256).digest()
    sig_b = _b64url_encode(signature)
    return f"{payload_b}.{sig_b}"


def _verify_reset_token(token: str) -> dict | None:
    secret = _reset_secret()
    if not secret:
        return None
    if not token:
        return None

    # Be tolerant to copied values from email clients:
    # allow full URL, surrounding quotes and wrapped whitespace.
    token = token.strip().strip("'\"")
    if token.startswith(("http://", "https://")):
        parsed = urlparse(token)
        qs_token = parse_qs(parsed.query).get("token", [])
        token = qs_token[0] if qs_token else token
    token = "".join(token.split())

    if "." not in token:
        return None
    payload_b, sig_b = token.split(".", 1)
    try:
        payload_raw = _b64url_decode(payload_b)
    except Exception:
        return None
    expected_sig = hmac.new(secret, payload_b.encode("utf-8"), hashlib.sha256).digest()
    try:
        provided_sig = _b64url_decode(sig_b)
    except Exception:
        return None
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


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotRequest(BaseModel):
    email: str


class ResetRequest(BaseModel):
    token: str
    password: str
    password2: str


def _cookie_secure() -> bool:
    raw = os.getenv("COOKIE_SECURE", "").strip()
    if raw:
        return raw not in ("0", "false", "False", "no", "NO")
    return False


@router.get("/me")
async def me(user: User = Depends(require_admin)) -> dict:
    return {"ok": True, "username": user.username}


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not _check_password(user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="Neplatné přihlašovací údaje")
    token = make_session_token(user.id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=session_ttl_seconds(),
        path="/",
    )
    return {"ok": True, "username": user.username}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@router.post("/forgot")
async def forgot(
    payload: ForgotRequest,
    db: Session = Depends(get_db),
) -> dict:
    user = db.query(User).filter(User.email == payload.email.strip()).first()
    if user:
        try:
            token = _make_reset_token(user)
            admin_base = (
                os.getenv("ADMIN_BASE_URL")
                or os.getenv("PUBLIC_ADMIN_URL")
                or "http://localhost:3012"
            ).rstrip("/")
            reset_link = f"{admin_base}/admin/reset?token={token}"
            subject = os.getenv("PASSWORD_RESET_SUBJECT") or "Obnova hesla"
            body = "\n".join(
                [
                    "Dobrý den,",
                    "",
                    "požádali jste o obnovu hesla.",
                    "Klikněte na odkaz níže a nastavte nové heslo:",
                    reset_link,
                    "",
                    "Pokud jste si obnovu nevyžádali, tento e-mail ignorujte.",
                ]
            )
            html_body = "\n".join(
                [
                    "<p>Dobrý den,</p>",
                    "<p>požádali jste o obnovu hesla.</p>",
                    f'<p><a href="{reset_link}">Klikněte zde a nastavte nové heslo</a></p>',
                    f'<p>Pokud odkaz nejde otevřít, zkopírujte: <br><a href="{reset_link}">{reset_link}</a></p>',
                    "<p>Pokud jste si obnovu nevyžádali, tento e-mail ignorujte.</p>",
                ]
            )
            send_email(subject=subject, recipients=[user.email], body=body, html_body=html_body)
        except Exception:
            # Neprozrazujeme detaily – bezpečnostní důvod
            logger.exception("Password reset email failed for user_id=%s", user.id)
    return {"ok": True, "message": "Pokud účet existuje, byl odeslán e-mail."}


@router.post("/reset")
async def reset(
    payload: ResetRequest,
    db: Session = Depends(get_db),
) -> dict:
    if payload.password != payload.password2:
        raise HTTPException(status_code=400, detail="Hesla se neshodují")
    data = _verify_reset_token(payload.token)
    if not data:
        raise HTTPException(status_code=400, detail="Neplatný nebo expirovaný token")
    user_id = data.get("uid")
    email = data.get("email")
    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == int(user_id)).first()
    if not user and email:
        user = db.query(User).filter(User.email == str(email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Uživatel nenalezen")
    user.password_hash = _hash_password(payload.password)
    db.commit()
    return {"ok": True}