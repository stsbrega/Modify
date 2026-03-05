"""Email sending abstraction with SMTP and console implementations."""

import logging
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send_email(self, to: str, subject: str, html_body: str) -> None: ...


class ConsoleEmailSender:
    """Logs emails to console — for development when SMTP is not configured."""

    async def send_email(self, to: str, subject: str, html_body: str) -> None:
        logger.info(
            f"\n{'='*60}\n"
            f"EMAIL (console mode — SMTP not configured)\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"Body:\n{html_body}\n"
            f"{'='*60}"
        )


class SMTPEmailSender:
    """Sends emails via SMTP using fastapi-mail."""

    def __init__(self) -> None:
        from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

        settings = get_settings()
        self._config = ConnectionConfig(
            MAIL_USERNAME=settings.smtp_user,
            MAIL_PASSWORD=settings.smtp_password,
            MAIL_FROM=settings.smtp_from_email,
            MAIL_FROM_NAME=settings.smtp_from_name,
            MAIL_PORT=settings.smtp_port,
            MAIL_SERVER=settings.smtp_host,
            MAIL_STARTTLS=settings.smtp_use_tls,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
        )
        self._mail = FastMail(self._config)
        self._MessageSchema = MessageSchema
        self._MessageType = MessageType

    async def send_email(self, to: str, subject: str, html_body: str) -> None:
        message = self._MessageSchema(
            subject=subject,
            recipients=[to],
            body=html_body,
            subtype=self._MessageType.html,
        )
        await self._mail.send_message(message)


def get_email_sender() -> EmailSender:
    """Factory: returns SMTPEmailSender if SMTP is configured, else ConsoleEmailSender."""
    settings = get_settings()
    if settings.smtp_host and settings.smtp_user:
        return SMTPEmailSender()
    return ConsoleEmailSender()


async def send_verification_email(to: str, token: str) -> None:
    """Send an email verification link."""
    settings = get_settings()
    verify_url = f"{settings.frontend_url}/auth/verify-email?token={token}"
    html = f"""
    <h2>Verify your email for ModdersOmni</h2>
    <p>Click the link below to verify your email address:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>This link expires in {settings.email_verification_expire_hours} hours.</p>
    <p>If you didn't create an account, you can ignore this email.</p>
    """
    sender = get_email_sender()
    await sender.send_email(to, "Verify your email — ModdersOmni", html)


async def send_inactivity_warning_email(
    to: str, display_name: str | None, deletion_date: str
) -> None:
    """Warn a user that their account will be deleted due to inactivity."""
    settings = get_settings()
    login_url = f"{settings.frontend_url}/auth/login"
    greeting = f"Hi {display_name}" if display_name else "Hi"
    html = f"""
    <h2>Your ModdersOmni account will be deleted</h2>
    <p>{greeting},</p>
    <p>It's been over a year since you last signed in to ModdersOmni.
       As a security precaution, we will delete your account and all associated data
       on <strong>{deletion_date}</strong>.</p>
    <p>To keep your account, simply <a href="{login_url}">sign in</a> before that date.</p>
    <p>If you no longer need your account, no action is required — your data will be
       removed automatically. You can always create a new account with the same email address.</p>
    <p>— The ModdersOmni Team</p>
    """
    sender = get_email_sender()
    await sender.send_email(to, "Your ModdersOmni account will be deleted soon", html)


async def send_password_reset_email(to: str, token: str) -> None:
    """Send a password reset link."""
    settings = get_settings()
    reset_url = f"{settings.frontend_url}/auth/reset-password?token={token}"
    html = f"""
    <h2>Reset your password</h2>
    <p>Click the link below to reset your password:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>This link expires in 1 hour.</p>
    <p>If you didn't request this, you can ignore this email.</p>
    """
    sender = get_email_sender()
    await sender.send_email(to, "Reset your password — ModdersOmni", html)
