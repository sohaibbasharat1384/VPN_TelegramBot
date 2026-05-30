"""Broadcast service: create and fan-out messages to a target audience."""
from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.enums import (
    BroadcastStatus,
    BroadcastTarget,
    ContentType,
    SubscriptionStatus,
)
from app.models.order import Subscription
from app.models.system import Broadcast
from app.models.user import User
from app.utils import telegram

# Telegram allows ~30 msg/s; stay well under to avoid 429s.
_BATCH = 25
_PAUSE_SECONDS = 1.0


async def create(
    db: AsyncSession,
    *,
    admin_id: int,
    content_type: ContentType,
    body: str,
    target: BroadcastTarget,
    media_path: str | None = None,
    target_user_ids: list[int] | None = None,
) -> Broadcast:
    broadcast = Broadcast(
        admin_id=admin_id,
        content_type=content_type,
        body=body,
        media_path=media_path,
        target=target,
        target_user_ids=target_user_ids,
        status=BroadcastStatus.queued,
    )
    db.add(broadcast)
    await db.flush()
    return broadcast


async def _audience(db: AsyncSession, broadcast: Broadcast) -> list[int]:
    """Resolve the target audience to a list of Telegram chat ids."""
    stmt = select(User.telegram_id).where(User.is_banned.is_(False))
    if broadcast.target == BroadcastTarget.active:
        stmt = stmt.where(
            User.id.in_(
                select(Subscription.user_id).where(
                    Subscription.status == SubscriptionStatus.active
                )
            )
        )
    elif broadcast.target == BroadcastTarget.specific:
        stmt = stmt.where(User.id.in_(broadcast.target_user_ids or []))
    rows = await db.execute(stmt)
    return [r[0] for r in rows.all()]


async def _send_one(token: str, chat_id: int, broadcast: Broadcast, media: bytes | None) -> bool:
    if broadcast.content_type == ContentType.text or media is None:
        return await telegram.send_message(token, chat_id, broadcast.body)
    if broadcast.content_type == ContentType.photo:
        return await telegram.send_photo(token, chat_id, media, caption=broadcast.body)
    if broadcast.content_type == ContentType.video:
        return await telegram.send_video(token, chat_id, media, caption=broadcast.body)
    filename = Path(broadcast.media_path or "file").name
    return await telegram.send_document(token, chat_id, media, filename, caption=broadcast.body)


async def dispatch(db: AsyncSession, broadcast_id: int) -> int:
    broadcast = await db.get(Broadcast, broadcast_id)
    if broadcast is None:
        raise NotFoundError(user_message="پیام همگانی یافت نشد.")

    broadcast.status = BroadcastStatus.sending
    await db.flush()

    media: bytes | None = None
    if broadcast.media_path and Path(broadcast.media_path).exists():
        media = Path(broadcast.media_path).read_bytes()

    token = settings.customer_bot_token
    chat_ids = await _audience(db, broadcast)
    sent = failed = 0
    for i, chat_id in enumerate(chat_ids, 1):
        ok = await _send_one(token, chat_id, broadcast, media)
        sent += int(ok)
        failed += int(not ok)
        if i % _BATCH == 0:
            await asyncio.sleep(_PAUSE_SECONDS)

    broadcast.sent_count = sent
    broadcast.failed_count = failed
    broadcast.status = BroadcastStatus.done
    await db.flush()
    return sent
