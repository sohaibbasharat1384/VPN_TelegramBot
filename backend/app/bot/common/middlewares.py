"""Aiogram middlewares: per-update DB session + customer provisioning + ban gate."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser

from app.bot.common import texts
from app.db.session import session_scope
from app.services import user_service


class SessionUserMiddleware(BaseMiddleware):
    """Opens a committed session for the whole update and injects `db` + `user`.

    Used as an outer middleware so every handler shares one transaction that
    commits on success and rolls back on error.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        async with session_scope() as db:
            data["db"] = db
            if tg_user is None or tg_user.is_bot:
                return await handler(event, data)

            user, created = await user_service.get_or_create(
                db,
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
            )
            data["user"] = user
            data["user_created"] = created

            if user.is_banned:
                await _reply_banned(event)
                return None
            return await handler(event, data)


async def _reply_banned(event: TelegramObject) -> None:
    if isinstance(event, Message):
        await event.answer(texts.BANNED)
    elif isinstance(event, CallbackQuery):
        await event.answer(texts.BANNED, show_alert=True)
