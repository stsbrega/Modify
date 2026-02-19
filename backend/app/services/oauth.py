"""OAuth provider abstraction for Google and Discord sign-in."""

import logging
import time
import uuid
from dataclasses import dataclass

from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAuth state store (CSRF protection)
# ---------------------------------------------------------------------------

# In-memory state store: maps state -> (provider, created_at)
# States expire after 10 minutes.
_STATE_TTL_SECONDS = 600
_oauth_states: dict[str, tuple[str, float]] = {}


def create_oauth_state(provider: str) -> str:
    """Generate and store a random OAuth state token for CSRF protection."""
    _purge_expired_states()
    state = str(uuid.uuid4())
    _oauth_states[state] = (provider, time.time())
    return state


def validate_oauth_state(state: str, provider: str) -> bool:
    """Validate and consume an OAuth state token. Returns True if valid."""
    _purge_expired_states()
    entry = _oauth_states.pop(state, None)
    if entry is None:
        return False
    stored_provider, created_at = entry
    if stored_provider != provider:
        return False
    if time.time() - created_at > _STATE_TTL_SECONDS:
        return False
    return True


def _purge_expired_states() -> None:
    """Remove expired entries from the state store."""
    now = time.time()
    expired = [k for k, (_, t) in _oauth_states.items() if now - t > _STATE_TTL_SECONDS]
    for k in expired:
        _oauth_states.pop(k, None)


@dataclass
class OAuthUserInfo:
    """Normalized user info from any OAuth provider."""

    provider: str  # "google", "discord"
    provider_user_id: str
    email: str
    email_verified: bool
    display_name: str | None = None
    avatar_url: str | None = None


class OAuthProvider:
    """Base OAuth provider interface."""

    provider_name: str = ""

    def get_authorization_url(self, state: str) -> str:
        raise NotImplementedError

    async def get_user_info(self, code: str) -> OAuthUserInfo:
        raise NotImplementedError

    def is_configured(self) -> bool:
        raise NotImplementedError


class GoogleOAuthProvider(OAuthProvider):
    provider_name = "google"

    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.google_client_id and settings.google_client_secret)

    def get_authorization_url(self, state: str) -> str:
        settings = get_settings()
        client = AsyncOAuth2Client(
            client_id=settings.google_client_id,
            redirect_uri=settings.google_redirect_uri,
            scope="openid email profile",
        )
        url, _ = client.create_authorization_url(
            self.AUTHORIZE_URL, state=state
        )
        return url

    async def get_user_info(self, code: str) -> OAuthUserInfo:
        settings = get_settings()
        async with AsyncOAuth2Client(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_redirect_uri,
        ) as client:
            await client.fetch_token(
                self.TOKEN_URL, code=code, grant_type="authorization_code"
            )
            resp = await client.get(self.USERINFO_URL)
            data = resp.json()

        return OAuthUserInfo(
            provider="google",
            provider_user_id=data["sub"],
            email=data["email"],
            email_verified=data.get("email_verified", False),
            display_name=data.get("name"),
            avatar_url=data.get("picture"),
        )


class DiscordOAuthProvider(OAuthProvider):
    provider_name = "discord"

    AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    USERINFO_URL = "https://discord.com/api/users/@me"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.discord_client_id and settings.discord_client_secret)

    def get_authorization_url(self, state: str) -> str:
        settings = get_settings()
        client = AsyncOAuth2Client(
            client_id=settings.discord_client_id,
            redirect_uri=settings.discord_redirect_uri,
            scope="identify email",
        )
        url, _ = client.create_authorization_url(
            self.AUTHORIZE_URL, state=state
        )
        return url

    async def get_user_info(self, code: str) -> OAuthUserInfo:
        settings = get_settings()
        async with AsyncOAuth2Client(
            client_id=settings.discord_client_id,
            client_secret=settings.discord_client_secret,
            redirect_uri=settings.discord_redirect_uri,
        ) as client:
            await client.fetch_token(
                self.TOKEN_URL, code=code, grant_type="authorization_code"
            )
            resp = await client.get(self.USERINFO_URL)
            data = resp.json()

        avatar_url = None
        if data.get("avatar"):
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png"
            )

        return OAuthUserInfo(
            provider="discord",
            provider_user_id=str(data["id"]),
            email=data["email"],
            email_verified=data.get("verified", False),
            display_name=data.get("global_name") or data.get("username"),
            avatar_url=avatar_url,
        )


_PROVIDERS: dict[str, OAuthProvider] = {
    "google": GoogleOAuthProvider(),
    "discord": DiscordOAuthProvider(),
}


def get_oauth_provider(name: str) -> OAuthProvider | None:
    """Get an OAuth provider by name. Returns None if not found."""
    return _PROVIDERS.get(name)


def get_configured_providers() -> list[str]:
    """Return the names of all OAuth providers that are fully configured."""
    return [name for name, p in _PROVIDERS.items() if p.is_configured()]
