"""Admin bot middleware: per-update session + admin authentication."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser
from sqlalchemy import select

from app.bot.admin import texts
from app.db.session import session_scope
from app.models.rbac import AdminUser


class AdminAuthMiddleware(BaseMiddleware):
    """Injects `db` and the authenticated `admin`; rejects non-admins."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        async with session_scope() as db:
            data["db"] = db
            if tg_user is None:
                return None
            admin = (
                await db.execute(select(AdminUser).where(AdminUser.telegram_id == tg_user.id))
            ).scalar_one_or_none()
            if admin is None or not admin.is_active:
                await _reject(event)
                return None
            data["admin"] = admin
            data["perms"] = set(admin.permission_codes)
            return await handler(event, data)


async def _reject(event: TelegramObject) -> None:
    if isinstance(event, Message):
        await event.answer(texts.NOT_ADMIN)
    elif isinstance(event, CallbackQuery):
        await event.answer(texts.NOT_ADMIN, show_alert=True)
