"""Permission helpers for admin bot handlers."""
from __future__ import annotations

from aiogram.types import CallbackQuery, Message

from app.bot.admin import texts


async def ensure(event: Message | CallbackQuery, perms: set[str], required: str) -> bool:
    """Return True if `required` is held; otherwise reply and return False."""
    if required in perms:
        return True
    if isinstance(event, CallbackQuery):
        await event.answer(texts.NO_PERMISSION, show_alert=True)
    else:
        await event.answer(texts.NO_PERMISSION)
    return False
