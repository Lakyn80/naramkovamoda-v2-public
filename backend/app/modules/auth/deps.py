from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db

from .session import SESSION_COOKIE, verify_session_token
import hmac
import os


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    payload = verify_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user_id = payload.get("uid")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


def require_admin_or_rag_seed(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    expected = os.getenv("RAG_SEED_TOKEN")
    if not expected:
        return None
    provided = request.headers.get("x-rag-seed-token") or ""
    if hmac.compare_digest(provided, expected):
        return None
    return require_admin(request=request, db=db)
