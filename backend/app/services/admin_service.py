"""Admin helpers: resolve admin Telegram chat ids and push admin notifications."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.rbac import AdminUser
from app.utils.telegram import send_message


async def admin_chat_ids(db: AsyncSession) -> list[int]:
    rows = await db.execute(
        select(AdminUser.telegram_id).where(
            AdminUser.telegram_id.isnot(None), AdminUser.is_active.is_(True)
        )
    )
    ids = {r[0] for r in rows.all() if r[0]}
    ids.update(settings.bootstrap_admin_ids)
    return list(ids)


async def notify_admins(db: AsyncSession, text: str) -> int:
    sent = 0
    for chat_id in await admin_chat_ids(db):
        if await send_message(settings.admin_bot_token, chat_id, text):
            sent += 1
    return sent
