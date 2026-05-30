"""Notification service: dedup-aware delivery of automated user alerts.

The `notifications` unique constraint (user_id, kind, reference_id) guarantees an
alert of a given kind for a given subscription is sent at most once.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import NotificationKind
from app.models.system import Notification
from app.models.user import User
from app.utils.telegram import send_message


async def _claim(
    db: AsyncSession, user_id: int, kind: NotificationKind, reference_id: int, payload: dict
) -> bool:
    """Insert a notification row; return False if it already existed (deduped)."""
    stmt = (
        pg_insert(Notification)
        .values(user_id=user_id, kind=kind, reference_id=reference_id, payload=payload)
        .on_conflict_do_nothing(index_elements=["user_id", "kind", "reference_id"])
        .returning(Notification.id)
    )
    result = (await db.execute(stmt)).scalar_one_or_none()
    return result is not None


async def notify(
    db: AsyncSession,
    user: User,
    kind: NotificationKind,
    text: str,
    *,
    reference_id: int = 0,
    payload: dict | None = None,
) -> bool:
    """Send a deduped notification to a user. Returns True if newly sent."""
    if user.is_banned:
        return False
    is_new = await _claim(db, user.id, kind, reference_id, payload or {})
    if not is_new:
        return False
    sent = await send_message(settings.customer_bot_token, user.telegram_id, text)
    if sent:
        await db.execute(
            Notification.__table__.update()
            .where(
                Notification.user_id == user.id,
                Notification.kind == kind,
                Notification.reference_id == reference_id,
            )
            .values(sent_at=datetime.now(UTC))
        )
    return sent
