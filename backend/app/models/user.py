import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")
    oauth_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Hardware specs (single-profile design)
    gpu_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    cpu_model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    ram_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vram_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_speed_ghz: Mapped[float | None] = mapped_column(Float, nullable=True)
    hardware_tier: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hardware_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_drives: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_active_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deletion_warning_sent_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    modlists: Mapped[list["Modlist"]] = relationship(back_populates="user")  # noqa: F821
    settings: Mapped["UserSettings | None"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    oauth_providers: Mapped[list["UserOAuthProvider"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
