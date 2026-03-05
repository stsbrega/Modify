"""Core authentication service: password hashing, JWT, refresh tokens."""

import hashlib
import uuid
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.refresh_token import RefreshToken
from app.models.email_verification import EmailVerification


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    email_verified: bool,
) -> tuple[str, int]:
    """Create a JWT access token. Returns (token, expires_in_seconds)."""
    settings = get_settings()
    expires_minutes = settings.access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)

    payload = {
        "sub": str(user_id),
        "email": email,
        "email_verified": email_verified,
        "exp": expire,
        "type": "access",
    }
    token = jwt.encode(
        payload, settings.secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expires_minutes * 60


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns claims or None."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def _hash_token(token: str) -> str:
    """SHA-256 hash a token for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_refresh_token(
    user_id: uuid.UUID, db: AsyncSession
) -> str:
    """Create an opaque refresh token, store its hash in DB. Returns the raw token."""
    settings = get_settings()
    raw_token = str(uuid.uuid4())
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_token)
    await db.flush()
    return raw_token


async def rotate_refresh_token(
    old_raw_token: str, db: AsyncSession
) -> tuple[str, uuid.UUID] | None:
    """Rotate a refresh token: revoke old, create new. Returns (new_token, user_id) or None."""
    old_hash = _hash_token(old_raw_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == old_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    old_token = result.scalar_one_or_none()
    if old_token is None:
        return None

    # Revoke old token
    old_token.revoked = True
    user_id = old_token.user_id

    # Create new token
    new_raw_token = await create_refresh_token(user_id, db)
    return new_raw_token, user_id


async def revoke_refresh_token(raw_token: str, db: AsyncSession) -> bool:
    """Revoke a specific refresh token. Returns True if found and revoked."""
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if token:
        token.revoked = True
        return True
    return False


async def revoke_all_refresh_tokens(
    user_id: uuid.UUID, db: AsyncSession
) -> None:
    """Revoke all refresh tokens for a user (logout-all)."""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    for token in result.scalars():
        token.revoked = True


def _get_serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key)


def generate_email_verification_token(user_id: uuid.UUID) -> str:
    """Generate a signed email verification token."""
    serializer = _get_serializer()
    return serializer.dumps(str(user_id), salt="email-verify")


def decode_email_verification_token(token: str) -> uuid.UUID | None:
    """Decode a signed email verification token. Returns user_id or None."""
    settings = get_settings()
    serializer = _get_serializer()
    try:
        user_id_str = serializer.loads(
            token,
            salt="email-verify",
            max_age=settings.email_verification_expire_hours * 3600,
        )
        return uuid.UUID(user_id_str)
    except (BadSignature, SignatureExpired, ValueError):
        return None


async def store_email_verification(
    user_id: uuid.UUID, token: str, db: AsyncSession
) -> None:
    """Store the hash of an email verification token."""
    settings = get_settings()
    token_hash = _hash_token(token)
    expires_at = datetime.utcnow() + timedelta(
        hours=settings.email_verification_expire_hours
    )
    verification = EmailVerification(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(verification)


def generate_password_reset_token(user_id: uuid.UUID) -> str:
    """Generate a signed password reset token."""
    serializer = _get_serializer()
    return serializer.dumps(str(user_id), salt="password-reset")


def decode_password_reset_token(token: str) -> uuid.UUID | None:
    """Decode a signed password reset token (1-hour max age)."""
    serializer = _get_serializer()
    try:
        user_id_str = serializer.loads(
            token, salt="password-reset", max_age=3600
        )
        return uuid.UUID(user_id_str)
    except (BadSignature, SignatureExpired, ValueError):
        return None
