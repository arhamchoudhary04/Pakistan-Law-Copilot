"""Password hashing and stateless session tokens, standard library only.

Passwords use PBKDF2-HMAC-SHA256 with a per-user random salt. Session tokens are a
compact HMAC-SHA256-signed ``payload.signature`` pair (a JWT without the dependency),
signed with ``settings.auth_secret``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.core.config import get_settings
from app.db.store import Account, get_account_store

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str, secret: str) -> str:
    return _b64encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())


_RESET_TTL_HOURS = 0.5  # password-reset tokens are short-lived (30 minutes)


def _create_token(user_id: str, typ: str, ttl_hours: float) -> str:
    secret = get_settings().auth_secret
    payload = {"sub": user_id, "typ": typ, "exp": int(time.time() + ttl_hours * 3600)}
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body, secret)}"


def _decode_token(token: str, expected_typ: str) -> str | None:
    """Return the user id from a valid token of the expected type, or None."""
    secret = get_settings().auth_secret
    try:
        body, signature = token.split(".")
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(body, secret)):
        return None
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("typ") != expected_typ or int(payload.get("exp", 0)) < time.time():
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


def create_token(user_id: str) -> str:
    return _create_token(user_id, "session", get_settings().auth_token_ttl_hours)


def decode_token(token: str) -> str | None:
    return _decode_token(token, "session")


def create_reset_token(user_id: str) -> str:
    return _create_token(user_id, "reset", _RESET_TTL_HOURS)


def decode_reset_token(token: str) -> str | None:
    return _decode_token(token, "reset")


def get_current_user(authorization: str = Header(default="")) -> Account:
    """FastAPI dependency: resolve the bearer token to the signed-in account."""
    token = authorization.removeprefix("Bearer ").strip()
    user_id = decode_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    account = get_account_store().get_account(user_id)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return account


# Reusable dependency annotation for signed-in routes.
CurrentUser = Annotated[Account, Depends(get_current_user)]
