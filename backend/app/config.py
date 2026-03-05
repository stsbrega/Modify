from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "ModdersOmni"
    debug: bool = False

    # CORS
    cors_origins: str = "http://localhost:4200,http://localhost"

    # Database
    database_url: str = "postgresql+asyncpg://modify:modify@localhost:5432/modify"

    # Nexus Mods
    nexus_api_key: str = ""

    # Custom Mod Source
    custom_source_api_url: str = ""
    custom_source_api_key: str = ""

    # Auth
    secret_key: str = "change-me-in-production-use-a-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@moddersomni.com"
    smtp_from_name: str = "ModdersOmni"
    smtp_use_tls: bool = True
    email_verification_expire_hours: int = 24

    # OAuth - Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/oauth/google/callback"

    # OAuth - Discord
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:8000/api/auth/oauth/discord/callback"

    # Account cleanup
    account_inactive_days: int = 365
    account_deletion_grace_days: int = 30
    account_cleanup_interval_hours: int = 24

    # Frontend URL (for email links and OAuth redirects)
    frontend_url: str = "http://localhost:4200"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
