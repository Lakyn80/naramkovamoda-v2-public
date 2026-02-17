from __future__ import annotations

from app.db.models import User
from app.modules.auth import router as auth_router


def test_reset_accepts_long_password(client, db_session, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_SALT", "test-reset-salt")

    admin = db_session.query(User).filter(User.username == "admin").first()
    assert admin is not None
    assert admin.email

    token = auth_router._make_reset_token(admin)
    new_password = "A" * 96

    res = client.post(
        "/api/auth/reset",
        json={"token": token, "password": new_password, "password2": new_password},
    )
    assert res.status_code == 200, res.text
    assert res.json().get("ok") is True

    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": new_password},
    )
    assert login.status_code == 200, login.text


def test_reset_accepts_token_copied_as_full_url(client, db_session, monkeypatch):
    monkeypatch.setenv("PASSWORD_RESET_SALT", "test-reset-salt")

    admin = db_session.query(User).filter(User.username == "admin").first()
    assert admin is not None

    token = auth_router._make_reset_token(admin)
    copied = f' "https://naramkovamoda.cz/admin/reset?token={token}" '

    password = "BezpecneHeslo123"
    res = client.post(
        "/api/auth/reset",
        json={"token": copied, "password": password, "password2": password},
    )
    assert res.status_code == 200, res.text
    assert res.json().get("ok") is True
