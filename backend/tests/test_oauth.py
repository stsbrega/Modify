"""Tests for OAuth endpoints and state management."""

import time
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.oauth import (
    _oauth_states,
    create_oauth_state,
    get_configured_providers,
    validate_oauth_state,
)


# ---------------------------------------------------------------------------
# Unit tests: OAuth state store
# ---------------------------------------------------------------------------


class TestOAuthStateStore:
    def setup_method(self):
        _oauth_states.clear()

    def test_create_state_returns_string(self):
        state = create_oauth_state("google")
        assert isinstance(state, str)
        assert len(state) > 0

    def test_validate_valid_state(self):
        state = create_oauth_state("google")
        assert validate_oauth_state(state, "google") is True

    def test_validate_consumes_state(self):
        """State should only be usable once (prevents replay attacks)."""
        state = create_oauth_state("google")
        assert validate_oauth_state(state, "google") is True
        assert validate_oauth_state(state, "google") is False

    def test_validate_wrong_provider(self):
        state = create_oauth_state("google")
        assert validate_oauth_state(state, "discord") is False

    def test_validate_unknown_state(self):
        assert validate_oauth_state("nonexistent-state", "google") is False

    def test_validate_expired_state(self):
        state = create_oauth_state("google")
        # Manually backdate the state
        provider, _ = _oauth_states[state]
        _oauth_states[state] = (provider, time.time() - 700)
        assert validate_oauth_state(state, "google") is False


# ---------------------------------------------------------------------------
# Unit tests: get_configured_providers
# ---------------------------------------------------------------------------


class TestGetConfiguredProviders:
    def test_returns_list(self):
        result = get_configured_providers()
        assert isinstance(result, list)

    def test_empty_when_no_credentials(self):
        """With empty config, no providers should be configured."""
        from app.services.oauth import _PROVIDERS

        with patch.dict(
            _PROVIDERS,
            {name: p for name, p in _PROVIDERS.items()},
        ):
            # Patch is_configured to return False for all providers
            for p in _PROVIDERS.values():
                p._orig_is_configured = p.is_configured
            with patch.object(
                _PROVIDERS["google"].__class__, "is_configured", return_value=False
            ), patch.object(
                _PROVIDERS["discord"].__class__, "is_configured", return_value=False
            ):
                result = get_configured_providers()
                assert result == []

    def test_only_returns_configured(self):
        """Only providers with credentials should appear."""
        result = get_configured_providers()
        # Each returned provider should report as configured
        from app.services.oauth import get_oauth_provider

        for name in result:
            provider = get_oauth_provider(name)
            assert provider is not None
            assert provider.is_configured() is True


# ---------------------------------------------------------------------------
# Integration tests: OAuth API endpoints
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_oauth_providers_endpoint(client):
    """GET /api/auth/oauth/providers should return configured providers list."""
    resp = await client.get("/api/auth/oauth/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


@pytest.mark.asyncio
async def test_oauth_providers_empty_when_unconfigured(client):
    """With no credentials, providers list should be empty."""
    from app.services.oauth import _PROVIDERS

    with patch.object(
        _PROVIDERS["google"].__class__, "is_configured", return_value=False
    ), patch.object(
        _PROVIDERS["discord"].__class__, "is_configured", return_value=False
    ):
        resp = await client.get("/api/auth/oauth/providers")
        assert resp.status_code == 200
        assert resp.json()["providers"] == []


@pytest.mark.asyncio
async def test_oauth_authorize_unknown_provider(client):
    """Requesting an unknown provider should return 400."""
    resp = await client.get("/api/auth/oauth/unknown_provider")
    assert resp.status_code == 400
    assert "Unknown OAuth provider" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_authorize_unconfigured_provider(client):
    """Requesting an unconfigured provider should return 501."""
    from app.services.oauth import _PROVIDERS

    with patch.object(
        _PROVIDERS["google"].__class__, "is_configured", return_value=False
    ):
        resp = await client.get("/api/auth/oauth/google")
        assert resp.status_code == 501
        assert "not configured" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_authorize_configured_provider(client):
    """Requesting a configured provider should return authorization URL."""
    from app.services.oauth import _PROVIDERS

    if not _PROVIDERS["google"].is_configured():
        pytest.skip("Google OAuth not configured")
    resp = await client.get("/api/auth/oauth/google")
    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "accounts.google.com" in data["authorization_url"]


@pytest.mark.asyncio
async def test_oauth_callback_missing_state(client):
    """Callback without state should return 400."""
    resp = await client.get(
        "/api/auth/oauth/google/callback",
        params={"code": "fake_code"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state(client):
    """Callback with invalid state should return 400."""
    resp = await client.get(
        "/api/auth/oauth/google/callback",
        params={"code": "fake_code", "state": "invalid-state"},
    )
    assert resp.status_code == 400
