"""Admin statistics."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, texts
from app.core.permissions import Perm
from app.services import stats_service
from app.utils.formatting import to_fa_digits, toman

router = Router()


@router.message(F.text == texts.BTN_STATS)
async def show_stats(message: Message, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.STATS_VIEW):
        return
    s = await stats_service.overview(db)
    await message.answer(
        texts.STATS_TEXT.format(
            total_users=to_fa_digits(s["total_users"]),
            active_users=to_fa_digits(s["active_users"]),
            daily_users=to_fa_digits(s["daily_users"]),
            active_subs=to_fa_digits(s["active_subscriptions"]),
            rev_day=toman(s["revenue_daily"]),
            rev_week=toman(s["revenue_weekly"]),
            rev_month=toman(s["revenue_monthly"]),
            wallet_total=toman(s["wallet_total"]),
            referral_total=toman(s["referral_total"]),
        )
    )
