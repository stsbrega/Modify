import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.llm.registry import get_public_registry
from app.models.user import User
from app.models.user_settings import UserSettings
from app.api.deps import get_current_user
from app.services.nexus_client import NexusModsClient

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter for sensitive endpoints
_raw_keys_requests: dict[str, list[float]] = defaultdict(list)
_RAW_KEYS_LIMIT = 10  # max requests per window
_RAW_KEYS_WINDOW = 60  # seconds

router = APIRouter()


_NOTIF_FIELDS = {"email_alerts", "mod_recommendations", "compat_warnings"}


class AppSettings(BaseModel):
    """Response model for GET /settings/ — always returns concrete values."""
    nexus_api_key: str = ""
    email_alerts: bool = True
    mod_recommendations: bool = True
    compat_warnings: bool = True

    model_config = {"from_attributes": True}


class AppSettingsUpdate(BaseModel):
    """Request model for PUT /settings/ — all fields optional for partial updates."""
    nexus_api_key: Optional[str] = None
    email_alerts: Optional[bool] = None
    mod_recommendations: Optional[bool] = None
    compat_warnings: Optional[bool] = None


async def _get_or_create_settings(
    user: User, db: AsyncSession
) -> UserSettings:
    """Get user settings, creating with defaults if missing."""
    if user.settings:
        return user.settings

    settings_row = UserSettings(user_id=user.id)
    db.add(settings_row)
    await db.flush()
    await db.refresh(user, ["settings"])
    return settings_row


# ── Provider Registry (public, no auth) ──────────────────────

@router.get("/llm-providers")
async def list_llm_providers():
    """Return the list of supported LLM providers for frontend rendering."""
    return get_public_registry()


# ── LLM API Keys (auth required) ─────────────────────────────

@router.get("/llm-keys")
async def get_llm_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's saved LLM API keys (provider_id → masked key)."""
    settings_row = await _get_or_create_settings(current_user, db)
    await db.commit()
    keys: dict = settings_row.llm_api_keys or {}
    # Mask keys for security: show only first 6 + last 4 chars
    masked = {}
    for provider_id, key in keys.items():
        if isinstance(key, str) and len(key) > 12:
            masked[provider_id] = key[:6] + "..." + key[-4:]
        elif isinstance(key, str) and key:
            masked[provider_id] = "***"
        # Skip empty keys
    return masked


@router.get("/llm-keys/raw")
async def get_llm_keys_raw(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return unmasked keys — used by the setup flow to pre-populate inputs.

    Rate-limited to 10 requests per minute per user to limit blast radius
    if an account token is compromised.
    """
    user_id = str(current_user.id)
    now = time.monotonic()
    # Prune old entries outside the window
    _raw_keys_requests[user_id] = [
        t for t in _raw_keys_requests[user_id] if now - t < _RAW_KEYS_WINDOW
    ]
    if len(_raw_keys_requests[user_id]) >= _RAW_KEYS_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Try again shortly.")
    _raw_keys_requests[user_id].append(now)

    settings_row = await _get_or_create_settings(current_user, db)
    await db.commit()
    keys: dict = settings_row.llm_api_keys or {}
    # Only return non-empty keys
    return {k: v for k, v in keys.items() if isinstance(v, str) and v}


@router.patch("/llm-keys")
async def patch_llm_keys(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Merge submitted keys into the user's llm_api_keys JSON.

    - Non-empty string values are upserted.
    - Empty string values remove that provider's key.
    """
    settings_row = await _get_or_create_settings(current_user, db)
    current_keys: dict = dict(settings_row.llm_api_keys or {})

    for provider_id, api_key in data.items():
        if not isinstance(api_key, str):
            continue
        if api_key:
            current_keys[provider_id] = api_key
        else:
            current_keys.pop(provider_id, None)

    settings_row.llm_api_keys = current_keys
    await db.commit()
    return {"status": "ok", "keys_saved": len(current_keys)}


# ── Nexus Key Validation ─────────────────────────────────────

@router.post("/validate-nexus-key")
async def validate_nexus_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test the user's Nexus API key against the Nexus v1 validate endpoint."""
    settings_row = await _get_or_create_settings(current_user, db)
    nexus_key = settings_row.nexus_api_key or ""
    if not nexus_key:
        return {"valid": False, "error": "No Nexus API key saved. Add one in Settings."}

    try:
        client = NexusModsClient(api_key=nexus_key)
        user_info = await client.validate_key()
        return {
            "valid": True,
            "username": user_info.get("name"),
            "is_premium": user_info.get("is_premium", False),
        }
    except Exception as e:
        logger.warning("Nexus key validation failed: %s", e)
        return {"valid": False, "error": str(e)[:200]}


# ── Full Settings (existing) ─────────────────────────────────

@router.get("/", response_model=AppSettings)
async def get_app_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings_row = await _get_or_create_settings(current_user, db)
    await db.commit()
    result = AppSettings.model_validate(settings_row)
    # Overlay notification prefs from JSON column
    prefs = settings_row.notification_prefs or {}
    result.email_alerts = prefs.get("email_alerts", True)
    result.mod_recommendations = prefs.get("mod_recommendations", True)
    result.compat_warnings = prefs.get("compat_warnings", True)
    return result


@router.put("/")
async def update_settings(
    data: AppSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings_row = await _get_or_create_settings(current_user, db)
    provided = data.model_dump(exclude_none=True)

    # Nexus API key → dedicated DB column
    if "nexus_api_key" in provided:
        settings_row.nexus_api_key = provided["nexus_api_key"]

    # Notification prefs → merge into JSON column (only overwrite provided fields)
    notif_update = {k: v for k, v in provided.items() if k in _NOTIF_FIELDS}
    if notif_update:
        current_prefs = dict(settings_row.notification_prefs or {})
        current_prefs.update(notif_update)
        settings_row.notification_prefs = current_prefs

    await db.commit()
    return {"status": "ok", "message": "Settings saved"}
