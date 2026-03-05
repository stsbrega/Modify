"""Tests for the core authentication service (pure-function subset).

Tests password hashing/verification, JWT access tokens, and signed
email-verification / password-reset tokens. DB-dependent functions
(refresh tokens) are not tested here — they require a live session.
"""

import uuid
from unittest.mock import patch

from app.services.auth import (
    _hash_token,
    create_access_token,
    decode_access_token,
    decode_email_verification_token,
    decode_password_reset_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_returns_string(self):
        hashed = hash_password("hunter2")
        assert isinstance(hashed, str)
        assert hashed != "hunter2"

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("my-secret")
        assert "my-secret" not in hashed

    def test_verify_correct_password(self):
        hashed = hash_password("correct-horse")
        assert verify_password("correct-horse", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-horse")
        assert verify_password("wrong-horse", hashed) is False

    def test_different_hashes_for_same_password(self):
        """bcrypt uses random salts, so same password produces different hashes."""
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2
        # But both should verify correctly
        assert verify_password("same-password", h1) is True
        assert verify_password("same-password", h2) is True


# ---------------------------------------------------------------------------
# SHA-256 token hashing (internal helper)
# ---------------------------------------------------------------------------


class TestHashToken:
    def test_deterministic(self):
        assert _hash_token("abc") == _hash_token("abc")

    def test_different_inputs_differ(self):
        assert _hash_token("abc") != _hash_token("xyz")

    def test_returns_hex_string(self):
        result = _hash_token("test")
        assert len(result) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------


class TestJwtAccessTokens:
    def _make_token(self, user_id=None, email="user@example.com", verified=True):
        uid = user_id or uuid.uuid4()
        token, expires_in = create_access_token(uid, email, verified)
        return token, expires_in, uid

    def test_create_returns_token_and_expiry(self):
        token, expires_in, _ = self._make_token()
        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(expires_in, int)
        assert expires_in > 0

    def test_decode_valid_token(self):
        token, _, uid = self._make_token(email="test@x.com", verified=False)
        claims = decode_access_token(token)
        assert claims is not None
        assert claims["sub"] == str(uid)
        assert claims["email"] == "test@x.com"
        assert claims["email_verified"] is False
        assert claims["type"] == "access"

    def test_decode_invalid_token_returns_none(self):
        assert decode_access_token("this.is.not.a.jwt") is None

    def test_decode_empty_string_returns_none(self):
        assert decode_access_token("") is None

    def test_decode_tampered_token_returns_none(self):
        token, _, _ = self._make_token()
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None

    def test_expiry_matches_settings(self):
        """expires_in should equal access_token_expire_minutes * 60."""
        from app.config import get_settings

        settings = get_settings()
        _, expires_in, _ = self._make_token()
        assert expires_in == settings.access_token_expire_minutes * 60


# ---------------------------------------------------------------------------
# Email verification tokens (itsdangerous signed)
# ---------------------------------------------------------------------------


class TestEmailVerificationTokens:
    def test_roundtrip(self):
        uid = uuid.uuid4()
        token = generate_email_verification_token(uid)
        decoded_uid = decode_email_verification_token(token)
        assert decoded_uid == uid

    def test_invalid_token_returns_none(self):
        assert decode_email_verification_token("garbage") is None

    def test_tampered_token_returns_none(self):
        uid = uuid.uuid4()
        token = generate_email_verification_token(uid)
        tampered = token + "extra"
        assert decode_email_verification_token(tampered) is None


# ---------------------------------------------------------------------------
# Password reset tokens (itsdangerous signed, 1-hour TTL)
# ---------------------------------------------------------------------------


class TestPasswordResetTokens:
    def test_roundtrip(self):
        uid = uuid.uuid4()
        token = generate_password_reset_token(uid)
        decoded_uid = decode_password_reset_token(token)
        assert decoded_uid == uid

    def test_invalid_token_returns_none(self):
        assert decode_password_reset_token("not-real") is None

    def test_tampered_token_returns_none(self):
        uid = uuid.uuid4()
        token = generate_password_reset_token(uid)
        tampered = token[:-3] + "ZZZ"
        assert decode_password_reset_token(tampered) is None

    def test_email_token_cannot_be_used_as_password_reset(self):
        """Tokens with different salts should not be interchangeable."""
        uid = uuid.uuid4()
        email_token = generate_email_verification_token(uid)
        assert decode_password_reset_token(email_token) is None

    def test_password_token_cannot_be_used_as_email_verification(self):
        uid = uuid.uuid4()
        pw_token = generate_password_reset_token(uid)
        assert decode_email_verification_token(pw_token) is None
