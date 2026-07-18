"""Authentication endpoints: sign up, log in, current account, and password reset."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.auth.security import (
    CurrentUser,
    create_reset_token,
    create_token,
    decode_reset_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.db.store import EmailTakenError, get_account_store
from app.models.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserOut,
)

router = APIRouter(prefix="/auth")


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest) -> AuthResponse:
    store = get_account_store()
    try:
        account = store.create_user(body.email, body.name, hash_password(body.password))
    except EmailTakenError as exc:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from exc
    return AuthResponse(
        token=create_token(account.id),
        user=UserOut(id=account.id, email=account.email, name=account.name),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    store = get_account_store()
    creds = store.find_credentials(body.email)
    if creds is None or not verify_password(body.password, creds[1]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    account = store.get_account(creds[0])
    assert account is not None
    return AuthResponse(
        token=create_token(account.id),
        user=UserOut(id=account.id, email=account.email, name=account.name),
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """Begin a password reset.

    Returns the same generic message whether or not the email exists (no account
    enumeration). When no email service is configured (``auth_dev_reset``), the
    reset token is returned directly so the flow is usable locally; in production
    the token would be emailed instead.
    """
    user_id = get_account_store().get_user_id_by_email(body.email)
    token = create_reset_token(user_id) if user_id else None
    message = "If an account exists for that email, a password-reset link has been sent."
    if get_settings().auth_dev_reset:
        return ForgotPasswordResponse(message=message, reset_token=token)
    return ForgotPasswordResponse(message=message)


@router.post("/reset-password", response_model=AuthResponse)
def reset_password(body: ResetPasswordRequest) -> AuthResponse:
    user_id = decode_reset_token(body.token)
    store = get_account_store()
    account = store.get_account(user_id) if user_id else None
    if account is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    store.update_password(account.id, hash_password(body.new_password))
    return AuthResponse(
        token=create_token(account.id),
        user=UserOut(id=account.id, email=account.email, name=account.name),
    )


@router.get("/me", response_model=UserOut)
def me(account: CurrentUser) -> UserOut:
    return UserOut(id=account.id, email=account.email, name=account.name)
