"""Password hashing, signed-token, and startup security-guard tests.

Pins down the hand-rolled auth guarantees: passwords reject tampering, tokens are
typed (reset != session) and expire, and production refuses to boot with insecure
defaults.
"""

import pytest

import app.auth.security as security
from app.core.config import DEFAULT_INSECURE_SECRET, Settings
from app.main import _enforce_security


def _patch_secret(monkeypatch, **overrides) -> Settings:
    settings = Settings(auth_secret="unit-test-secret", **overrides)
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    return settings


# ---- password hashing ----


def test_password_round_trip_and_rejects_wrong_password():
    stored = security.hash_password("correct horse battery staple")
    assert stored.startswith("pbkdf2_sha256$")
    assert security.verify_password("correct horse battery staple", stored)
    assert not security.verify_password("wrong password", stored)


def test_verify_password_rejects_malformed_hash():
    assert not security.verify_password("anything", "not-a-valid-hash")


def test_hashes_are_salted_and_differ_for_same_password():
    assert security.hash_password("same") != security.hash_password("same")


# ---- signed session / reset tokens ----


def test_session_token_round_trip(monkeypatch):
    _patch_secret(monkeypatch)
    assert security.decode_token(security.create_token("user-1")) == "user-1"


def test_reset_token_cannot_be_used_as_session_token(monkeypatch):
    _patch_secret(monkeypatch)
    reset = security.create_reset_token("user-1")
    assert security.decode_token(reset) is None  # typed: reset != session
    assert security.decode_reset_token(reset) == "user-1"


def test_tampered_token_is_rejected(monkeypatch):
    _patch_secret(monkeypatch)
    token = security.create_token("user-1")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert security.decode_token(tampered) is None


def test_expired_token_is_rejected(monkeypatch):
    _patch_secret(monkeypatch, auth_token_ttl_hours=-1)  # already expired on creation
    assert security.decode_token(security.create_token("user-1")) is None


def test_token_signed_with_a_different_secret_is_rejected(monkeypatch):
    _patch_secret(monkeypatch)
    token = security.create_token("user-1")
    # Rotate the signing secret; the previously issued token must no longer verify.
    monkeypatch.setattr(security, "get_settings", lambda: Settings(auth_secret="rotated-secret"))
    assert security.decode_token(token) is None


# ---- startup security guard ----


def test_insecure_defaults_are_flagged():
    settings = Settings(auth_secret=DEFAULT_INSECURE_SECRET, auth_dev_reset=True)
    assert len(settings.security_problems()) == 2


def test_secure_config_has_no_problems():
    settings = Settings(auth_secret="a-long-random-secret", auth_dev_reset=False)
    assert settings.security_problems() == []


def test_production_refuses_to_start_with_insecure_defaults():
    prod = Settings(app_env="production", auth_secret=DEFAULT_INSECURE_SECRET)
    assert prod.is_production
    with pytest.raises(RuntimeError, match="insecure auth config"):
        _enforce_security(prod)


def test_dev_only_warns_and_starts():
    dev = Settings(app_env="dev", auth_secret=DEFAULT_INSECURE_SECRET)
    assert not dev.is_production
    _enforce_security(dev)  # dev is lenient: logs a warning, must not raise
