import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )

    nexus_api_key: Mapped[str] = mapped_column(String(255), default="")

    # DEPRECATED: Legacy per-provider columns — no longer read or written.
    # LLM keys are now stored in the `llm_api_keys` JSON column.
    # Columns kept to avoid a DB migration; safe to drop in a future migration.
    llm_provider: Mapped[str] = mapped_column(String(20), default="ollama")
    ollama_base_url: Mapped[str] = mapped_column(
        String(255), default="http://localhost:11434/v1"
    )
    ollama_model: Mapped[str] = mapped_column(String(100), default="llama3.1:8b")
    groq_api_key: Mapped[str] = mapped_column(String(255), default="")
    groq_model: Mapped[str] = mapped_column(
        String(100), default="llama-3.3-70b-versatile"
    )
    together_api_key: Mapped[str] = mapped_column(String(255), default="")
    together_model: Mapped[str] = mapped_column(
        String(255), default="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    )
    huggingface_api_key: Mapped[str] = mapped_column(String(255), default="")
    huggingface_model: Mapped[str] = mapped_column(
        String(255), default="meta-llama/Llama-3.1-8B-Instruct"
    )
    custom_source_api_url: Mapped[str] = mapped_column(String(255), default="")
    custom_source_api_key: Mapped[str] = mapped_column(String(255), default="")

    # Unified JSON store for all LLM API keys: {"provider_id": "api_key", ...}
    llm_api_keys: Mapped[dict] = mapped_column(JSON, default=dict)

    # Notification preferences: {"email_alerts": true, "mod_recommendations": true, ...}
    notification_prefs: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="settings")  # noqa: F821
