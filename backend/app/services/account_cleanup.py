"""Periodic cleanup of inactive user accounts.

Runs as a background asyncio task (see main.py lifespan). Two phases:
1. Send warning emails to users inactive for `account_inactive_days`.
2. Delete accounts that were warned `account_deletion_grace_days` ago
   and still haven't logged back in.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.database import async_session
from app.models.user import User
from app.services.email import send_inactivity_warning_email

logger = logging.getLogger(__name__)


async def send_inactivity_warnings(session) -> int:
    """Email users who have been inactive for over a year (and not yet warned)."""
    settings = get_settings()
    cutoff = datetime.utcnow() - timedelta(days=settings.account_inactive_days)

    result = await session.execute(
        select(User).where(
            User.last_active_at < cutoff,
            User.last_active_at.isnot(None),
            User.deletion_warning_sent_at.is_(None),
        )
    )
    users = result.scalars().all()

    warned = 0
    for user in users:
        deletion_date = (
            datetime.utcnow() + timedelta(days=settings.account_deletion_grace_days)
        ).strftime("%B %d, %Y")
        try:
            await send_inactivity_warning_email(
                to=user.email,
                display_name=user.display_name,
                deletion_date=deletion_date,
            )
            user.deletion_warning_sent_at = datetime.utcnow()
            warned += 1
        except Exception:
            logger.exception("Failed to send inactivity warning to %s", user.email)

    return warned


async def delete_expired_accounts(session) -> int:
    """Delete accounts whose grace period has expired and who still haven't logged in."""
    settings = get_settings()
    inactive_cutoff = datetime.utcnow() - timedelta(days=settings.account_inactive_days)
    grace_cutoff = datetime.utcnow() - timedelta(
        days=settings.account_deletion_grace_days
    )

    result = await session.execute(
        select(User).where(
            User.deletion_warning_sent_at < grace_cutoff,
            User.last_active_at < inactive_cutoff,
            User.last_active_at.isnot(None),
        )
    )
    users = result.scalars().all()

    deleted = 0
    for user in users:
        logger.info(
            "Deleting inactive account: %s (last active: %s, warned: %s)",
            user.email,
            user.last_active_at,
            user.deletion_warning_sent_at,
        )
        await session.delete(user)
        deleted += 1

    return deleted


async def run_cleanup_cycle() -> None:
    """Execute one full cleanup cycle (warn + delete)."""
    async with async_session() as session:
        warned = await send_inactivity_warnings(session)
        deleted = await delete_expired_accounts(session)
        await session.commit()

        if warned or deleted:
            logger.info(
                "Account cleanup: %d warnings sent, %d accounts deleted",
                warned,
                deleted,
            )
