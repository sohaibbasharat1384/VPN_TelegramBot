"""Referral / invite-friends."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import texts
from app.models.user import User
from app.services import referral_service
from app.utils.formatting import to_fa_digits, toman

router = Router()


@router.message(F.text == texts.BTN_REFERRAL)
async def referral_info(message: Message, db: AsyncSession, user: User, bot: Bot) -> None:
    me = await bot.me()
    link = f"https://t.me/{me.username}?start={user.referral_code}"
    stats = await referral_service.stats_for(db, user.id)
    await message.answer(
        texts.REFERRAL_INFO.format(
            link=link,
            total=to_fa_digits(stats["total"]),
            earned=toman(stats["earned"]),
        )
    )
