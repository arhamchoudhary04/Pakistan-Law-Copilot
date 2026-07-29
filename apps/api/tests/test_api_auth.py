"""``/auth/*`` over HTTP: status codes, validation, and the no-enumeration promise.

These exercise the layer the unit tests skip — FastAPI routing, the
``get_current_user`` dependency, and request validation at the boundary.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth, signup

PASSWORD = "correct-horse"


# ---- signup ----


def test_signup_returns_a_token_that_authenticates_me(client: TestClient):
    resp = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "name": "New User", "password": PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["name"] == "New User"

    me = client.get("/auth/me", headers=auth(body["token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_signup_never_returns_the_password_hash(client: TestClient):
    resp = client.post(
        "/auth/signup", json={"email": "leak@example.com", "name": "L", "password": PASSWORD}
    )
    assert "password" not in resp.text.lower()


def test_duplicate_signup_is_a_conflict(client: TestClient):
    signup(client, "dup@example.com")
    resp = client.post(
        "/auth/signup", json={"email": "dup@example.com", "name": "Again", "password": PASSWORD}
    )
    assert resp.status_code == 409


def test_signup_email_is_normalized_so_login_is_case_insensitive(client: TestClient):
    signup(client, "MiXeD@Example.COM")
    resp = client.post("/auth/login", json={"email": "mixed@example.com", "password": PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "mixed@example.com"


def test_signup_rejects_invalid_input(client: TestClient):
    bad_email = client.post(
        "/auth/signup", json={"email": "not-an-email", "name": "N", "password": PASSWORD}
    )
    short_password = client.post(
        "/auth/signup", json={"email": "ok@example.com", "name": "N", "password": "123"}
    )
    blank_name = client.post(
        "/auth/signup", json={"email": "ok2@example.com", "name": "", "password": PASSWORD}
    )
    assert bad_email.status_code == 422
    assert short_password.status_code == 422
    assert blank_name.status_code == 422


# ---- login ----


def test_login_with_correct_credentials(client: TestClient):
    signup(client, "log@example.com")
    resp = client.post("/auth/login", json={"email": "log@example.com", "password": PASSWORD})
    assert resp.status_code == 200
    assert client.get("/auth/me", headers=auth(resp.json()["token"])).status_code == 200


def test_wrong_password_and_unknown_email_are_indistinguishable(client: TestClient):
    """Same status and same message, so login can't be used to enumerate accounts."""
    signup(client, "known@example.com")
    wrong_password = client.post(
        "/auth/login", json={"email": "known@example.com", "password": "not-the-password"}
    )
    unknown_email = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


# ---- the authentication dependency ----


def test_me_requires_a_valid_bearer_token(client: TestClient):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth("garbage")).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_a_token_signed_with_another_secret_is_rejected(client: TestClient, monkeypatch):
    """A forged token must not authenticate, even if it is structurally valid."""
    import app.auth.security as security
    from app.core.config import Settings

    token = security.create_token("some-user")  # signed with the test secret
    monkeypatch.setattr(security, "get_settings", lambda: Settings(auth_secret="different-secret"))
    assert client.get("/auth/me", headers=auth(token)).status_code == 401


def test_token_for_a_deleted_account_is_rejected(client: TestClient, tmp_path):
    """The token still verifies, but the account is gone — must not authenticate."""
    import sqlite3

    from app.core.config import get_settings

    token = signup(client, "vanishing@example.com")
    assert client.get("/auth/me", headers=auth(token)).status_code == 200

    with sqlite3.connect(get_settings().app_db_path) as conn:
        conn.execute("DELETE FROM users WHERE email = ?", ("vanishing@example.com",))

    assert client.get("/auth/me", headers=auth(token)).status_code == 401


# ---- password reset ----


def test_forgot_password_does_not_reveal_whether_an_email_exists(client: TestClient):
    signup(client, "real@example.com")
    real = client.post("/auth/forgot-password", json={"email": "real@example.com"})
    fake = client.post("/auth/forgot-password", json={"email": "ghost@example.com"})

    assert real.status_code == fake.status_code == 200
    assert real.json()["message"] == fake.json()["message"]
    # Only the existing account gets a usable token (dev mode returns it inline).
    assert real.json()["reset_token"] is not None
    assert fake.json()["reset_token"] is None


def test_reset_password_replaces_the_old_password(client: TestClient):
    signup(client, "reset@example.com")
    reset_token = client.post(
        "/auth/forgot-password", json={"email": "reset@example.com"}
    ).json()["reset_token"]

    resp = client.post(
        "/auth/reset-password", json={"token": reset_token, "new_password": "brand-new-password"}
    )
    assert resp.status_code == 200
    assert client.get("/auth/me", headers=auth(resp.json()["token"])).status_code == 200

    old = client.post("/auth/login", json={"email": "reset@example.com", "password": PASSWORD})
    new = client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "brand-new-password"}
    )
    assert old.status_code == 401
    assert new.status_code == 200


def test_a_reset_token_cannot_be_used_as_a_session_token(client: TestClient):
    """The typed-token guarantee, asserted through HTTP rather than in-process."""
    signup(client, "typed@example.com")
    reset_token = client.post(
        "/auth/forgot-password", json={"email": "typed@example.com"}
    ).json()["reset_token"]

    assert client.get("/auth/me", headers=auth(reset_token)).status_code == 401


def test_reset_with_an_invalid_token_is_rejected(client: TestClient):
    resp = client.post(
        "/auth/reset-password", json={"token": "not-a-token", "new_password": "whatever-123"}
    )
    assert resp.status_code == 400
