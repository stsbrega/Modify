"""OAuth provider abstraction for Google, Discord, and Apple sign-in."""

import logging
import time
import uuid
from dataclasses import dataclass

import httpx
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

    provider: str  # "google", "discord", "apple"
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


class AppleOAuthProvider(OAuthProvider):
    provider_name = "apple"

    AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
    TOKEN_URL = "https://appleid.apple.com/auth/token"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(
            settings.apple_client_id
            and settings.apple_team_id
            and settings.apple_key_id
            and settings.apple_private_key
        )

    def get_authorization_url(self, state: str) -> str:
        settings = get_settings()
        client = AsyncOAuth2Client(
            client_id=settings.apple_client_id,
            redirect_uri=settings.apple_redirect_uri,
            scope="name email",
        )
        url, _ = client.create_authorization_url(
            self.AUTHORIZE_URL,
            state=state,
            response_mode="form_post",
        )
        return url

    async def get_user_info(self, code: str) -> OAuthUserInfo:
        settings = get_settings()
        # Apple uses a JWT client_secret generated from a private key
        from authlib.jose import jwt as authlib_jwt
        import time

        now = int(time.time())
        claims = {
            "iss": settings.apple_team_id,
            "iat": now,
            "exp": now + 300,
            "aud": "https://appleid.apple.com",
            "sub": settings.apple_client_id,
        }
        header = {"kid": settings.apple_key_id}
        client_secret = authlib_jwt.encode(
            header, claims, settings.apple_private_key
        ).decode("utf-8")

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                self.TOKEN_URL,
                data={
                    "client_id": settings.apple_client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.apple_redirect_uri,
                },
            )
            token_data = resp.json()

        # Decode the id_token to get user info
        id_token = token_data.get("id_token", "")
        # Apple's id_token is a JWT — decode without verification for user info
        # (token was just received directly from Apple's token endpoint)
        from jose import jwt as jose_jwt

        claims = jose_jwt.get_unverified_claims(id_token)

        return OAuthUserInfo(
            provider="apple",
            provider_user_id=claims.get("sub", ""),
            email=claims.get("email", ""),
            email_verified=claims.get("email_verified", False),
            display_name=None,  # Apple only provides name on first sign-in via form_post
            avatar_url=None,
        )


_PROVIDERS: dict[str, OAuthProvider] = {
    "google": GoogleOAuthProvider(),
    "discord": DiscordOAuthProvider(),
    "apple": AppleOAuthProvider(),
}


def get_oauth_provider(name: str) -> OAuthProvider | None:
    """Get an OAuth provider by name. Returns None if not found."""
    return _PROVIDERS.get(name)


def get_configured_providers() -> list[str]:
    """Return the names of all OAuth providers that are fully configured."""
    return [name for name, p in _PROVIDERS.items() if p.is_configured()]
