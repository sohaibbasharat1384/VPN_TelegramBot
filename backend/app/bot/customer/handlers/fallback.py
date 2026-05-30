"""Catch-all for unrecognized input outside any active flow."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from app.bot.common import texts
from app.bot.customer import keyboards

router = Router()


@router.message(StateFilter(None))
async def unknown(message: Message) -> None:
    await message.answer(texts.UNKNOWN, reply_markup=keyboards.main_menu())
