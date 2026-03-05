"""Authentication API routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.user_oauth_provider import UserOAuthProvider
from app.models.user_settings import UserSettings
from app.schemas.auth import (
    ForgotPasswordRequest,
    HardwareResponse,
    HardwareUpdate,
    LoginRequest,
    OAuthProviderInfo,
    PasswordChangeRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    UserUpdate,
    VerifyEmailRequest,
)
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_email_verification_token,
    decode_password_reset_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    store_email_verification,
    verify_password,
)
from app.services.email import send_password_reset_email, send_verification_email
from app.services.oauth import (
    create_oauth_state,
    get_configured_providers,
    get_oauth_provider,
    validate_oauth_state,
)
from app.services.tier_classifier import classify_hardware_tier
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE, path="/api/auth", samesite="none", secure=True,
    )


def _stamp_activity(user: User) -> None:
    """Record an authentication event and cancel any pending deletion warning."""
    user.last_active_at = datetime.utcnow()
    if user.deletion_warning_sent_at is not None:
        user.deletion_warning_sent_at = None


def _build_user_response(user: User) -> UserResponse:
    hardware = None
    if user.gpu_model or user.cpu_model or user.ram_gb or user.vram_mb:
        hardware = HardwareResponse(
            gpu_model=user.gpu_model,
            cpu_model=user.cpu_model,
            ram_gb=user.ram_gb,
            vram_mb=user.vram_mb,
            cpu_cores=user.cpu_cores,
            cpu_speed_ghz=user.cpu_speed_ghz,
            hardware_tier=user.hardware_tier,
            hardware_raw_text=user.hardware_raw_text,
        )
    connected = [
        OAuthProviderInfo(provider=op.provider, connected_at=op.connected_at)
        for op in user.oauth_providers
    ]
    return UserResponse(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        auth_provider=user.auth_provider,
        connected_providers=connected,
        hardware=hardware,
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        auth_provider="local",
    )
    db.add(user)
    await db.flush()

    _stamp_activity(user)

    # Create default settings
    settings_row = UserSettings(user_id=user.id)
    db.add(settings_row)

    # Generate email verification token and send
    verification_token = generate_email_verification_token(user.id)
    await store_email_verification(user.id, verification_token, db)
    await db.commit()

    # Send verification email (non-blocking — errors are logged, not raised)
    try:
        await send_verification_email(user.email, verification_token)
    except Exception:
        logger.exception("Failed to send verification email")

    # Issue tokens
    access_token, expires_in = create_access_token(
        user.id, user.email, user.email_verified
    )
    refresh_raw = await create_refresh_token(user.id, db)
    await db.commit()

    _set_refresh_cookie(response, refresh_raw)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    _stamp_activity(user)

    access_token, expires_in = create_access_token(
        user.id, user.email, user.email_verified
    )
    refresh_raw = await create_refresh_token(user.id, db)
    await db.commit()

    _set_refresh_cookie(response, refresh_raw)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    old_token = request.cookies.get(REFRESH_COOKIE)
    if not old_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    result = await rotate_refresh_token(old_token, db)
    if result is None:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_raw_token, user_id = result
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    _stamp_activity(user)

    access_token, expires_in = create_access_token(
        user.id, user.email, user.email_verified
    )
    await db.commit()

    _set_refresh_cookie(response, new_raw_token)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    old_token = request.cookies.get(REFRESH_COOKIE)
    if old_token:
        await revoke_refresh_token(old_token, db)
        await db.commit()
    _clear_refresh_cookie(response)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return _build_user_response(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    await db.commit()
    await db.refresh(user)
    return _build_user_response(user)


# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------


@router.get("/me/hardware", response_model=HardwareResponse | None)
async def get_hardware(user: User = Depends(get_current_user)):
    if not user.gpu_model and not user.cpu_model and not user.ram_gb and not user.vram_mb:
        return None
    return HardwareResponse(
        gpu_model=user.gpu_model,
        cpu_model=user.cpu_model,
        ram_gb=user.ram_gb,
        vram_mb=user.vram_mb,
        cpu_cores=user.cpu_cores,
        cpu_speed_ghz=user.cpu_speed_ghz,
        hardware_tier=user.hardware_tier,
        hardware_raw_text=user.hardware_raw_text,
        storage_drives=user.storage_drives,
    )


@router.put("/me/hardware", response_model=HardwareResponse)
async def update_hardware(
    data: HardwareUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    # Run tier classification on updated specs
    tier_result = classify_hardware_tier(
        gpu=user.gpu_model,
        vram_mb=user.vram_mb,
        cpu=user.cpu_model,
        ram_gb=user.ram_gb,
        cpu_cores=user.cpu_cores,
        cpu_speed_ghz=user.cpu_speed_ghz,
    )
    user.hardware_tier = tier_result["tier"]

    await db.commit()
    await db.refresh(user)

    return HardwareResponse(
        gpu_model=user.gpu_model,
        cpu_model=user.cpu_model,
        ram_gb=user.ram_gb,
        vram_mb=user.vram_mb,
        cpu_cores=user.cpu_cores,
        cpu_speed_ghz=user.cpu_speed_ghz,
        hardware_tier=user.hardware_tier,
        hardware_raw_text=user.hardware_raw_text,
        storage_drives=user.storage_drives,
    )


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------


@router.post("/verify-email")
async def verify_email_endpoint(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = decode_email_verification_token(data.token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        return {"status": "ok", "message": "Email already verified"}

    user.email_verified = True
    await db.commit()
    return {"status": "ok", "message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.email_verified:
        return {"status": "ok", "message": "Email already verified"}

    verification_token = generate_email_verification_token(user.id)
    await store_email_verification(user.id, verification_token, db)
    await db.commit()

    try:
        await send_verification_email(user.email, verification_token)
    except Exception:
        logger.exception("Failed to send verification email")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )

    return {"status": "ok", "message": "Verification email sent"}


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Always return success to prevent email enumeration
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user and user.password_hash:
        token = generate_password_reset_token(user.id)
        try:
            await send_password_reset_email(user.email, token)
        except Exception:
            logger.exception("Failed to send password reset email")

    return {"status": "ok", "message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = decode_password_reset_token(data.token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.password_hash = hash_password(data.new_password)
    # Revoke all refresh tokens (force re-login)
    await revoke_all_refresh_tokens(user.id, db)
    await db.commit()

    return {"status": "ok", "message": "Password reset successfully"}


# ---------------------------------------------------------------------------
# Password Change (for logged-in users)
# ---------------------------------------------------------------------------


@router.post("/change-password")
async def change_password(
    data: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth-only accounts",
        )

    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"status": "ok", "message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# OAuth
# ---------------------------------------------------------------------------


@router.get("/oauth/providers")
async def oauth_providers():
    """Return a list of OAuth providers that are currently configured."""
    return {"providers": get_configured_providers()}


@router.get("/oauth/{provider}")
async def oauth_authorize(provider: str):
    """Return the OAuth authorization URL for the given provider."""
    oauth = get_oauth_provider(provider)
    if oauth is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OAuth provider: {provider}",
        )

    if not oauth.is_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth provider '{provider}' is not configured",
        )

    state = create_oauth_state(provider)
    url = oauth.get_authorization_url(state)
    return {"authorization_url": url, "state": state}


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth callback: exchange code, create/link account, redirect to frontend."""
    settings = get_settings()

    def _error_redirect(error_code: str) -> RedirectResponse:
        """Redirect to frontend callback with an error query parameter."""
        url = f"{settings.frontend_url}/auth/callback?error={error_code}"
        return RedirectResponse(url=url)

    # Google/Discord may redirect with ?error=... when user denies consent
    if error:
        logger.warning(f"OAuth {provider} callback received error: {error}")
        return _error_redirect(error)

    if not code:
        return _error_redirect("missing_code")

    oauth = get_oauth_provider(provider)
    if oauth is None or not oauth.is_configured():
        return _error_redirect("provider_unavailable")

    # Validate state to prevent CSRF
    if not state or not validate_oauth_state(state, provider):
        return _error_redirect("invalid_state")

    try:
        user_info = await oauth.get_user_info(code)
    except Exception:
        logger.exception(f"OAuth {provider} token exchange failed")
        return _error_redirect("exchange_failed")

    # Check junction table for existing provider link
    result = await db.execute(
        select(UserOAuthProvider).where(
            UserOAuthProvider.provider == user_info.provider,
            UserOAuthProvider.provider_user_id == user_info.provider_user_id,
        )
    )
    link = result.scalar_one_or_none()

    if link:
        # Existing linked user — sign in
        user = await db.get(User, link.user_id)
    else:
        # Check if email already exists (link provider to existing account)
        result = await db.execute(
            select(User).where(User.email == user_info.email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            # Create new user
            user = User(
                email=user_info.email,
                email_verified=user_info.email_verified,
                display_name=user_info.display_name,
                avatar_url=user_info.avatar_url,
                auth_provider=user_info.provider,
            )
            db.add(user)
            await db.flush()

            # Create default settings
            settings_row = UserSettings(user_id=user.id)
            db.add(settings_row)
        else:
            # Update profile from provider if needed
            if user_info.email_verified:
                user.email_verified = True
            if user_info.avatar_url and not user.avatar_url:
                user.avatar_url = user_info.avatar_url

        # Add provider link to junction table
        oauth_link = UserOAuthProvider(
            user_id=user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
        )
        db.add(oauth_link)

    _stamp_activity(user)

    # Issue tokens
    access_token, expires_in = create_access_token(
        user.id, user.email, user.email_verified
    )
    refresh_raw = await create_refresh_token(user.id, db)
    await db.commit()

    # Redirect to frontend with access token
    redirect_url = f"{settings.frontend_url}/auth/callback?token={access_token}"
    redirect_response = RedirectResponse(url=redirect_url)
    _set_refresh_cookie(redirect_response, refresh_raw)
    return redirect_response


# ---------------------------------------------------------------------------
# Connected Accounts
# ---------------------------------------------------------------------------


@router.get("/me/connected-accounts", response_model=list[OAuthProviderInfo])
async def get_connected_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserOAuthProvider).where(UserOAuthProvider.user_id == user.id)
    )
    links = result.scalars().all()
    return [
        OAuthProviderInfo(provider=link.provider, connected_at=link.connected_at)
        for link in links
    ]


@router.delete("/me/connected-accounts/{provider}")
async def disconnect_account(
    provider: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Prevent lockout: must have password OR another provider remaining
    result = await db.execute(
        select(UserOAuthProvider).where(UserOAuthProvider.user_id == user.id)
    )
    links = result.scalars().all()
    target = next((lnk for lnk in links if lnk.provider == provider), None)

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider}' is not connected",
        )

    has_password = user.password_hash is not None
    other_providers = [lnk for lnk in links if lnk.provider != provider]

    if not has_password and not other_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disconnect your only sign-in method. Set a password first.",
        )

    await db.delete(target)
    await db.commit()
    return {"status": "ok", "message": f"{provider} disconnected"}
