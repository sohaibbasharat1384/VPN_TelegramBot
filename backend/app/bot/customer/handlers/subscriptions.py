"""My subscriptions + renewal."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import delivery, texts
from app.bot.customer import keyboards
from app.core.exceptions import DomainError, InsufficientBalanceError
from app.models.user import User
from app.services import order_service, subscription_service
from app.utils.formatting import gb, human_bytes, jalali

router = Router()


def _sub_text(sub) -> str:
    return texts.SUB_ROW.format(
        title=gb(sub.data_limit_bytes // 1024**3),
        expires=jalali(sub.expires_at),
        used=human_bytes(sub.data_used_bytes),
        limit=human_bytes(sub.data_limit_bytes),
        status=texts.STATUS_FA.get(sub.status.value, sub.status.value),
    )


@router.message(F.text == texts.BTN_MY_SUBS)
async def my_subs(message: Message, db: AsyncSession, user: User) -> None:
    subs = await subscription_service.list_for_user(db, user.id)
    if not subs:
        await message.answer(texts.NO_ACTIVE_SUBS)
        return
    for sub in subs:
        await message.answer(
            f"{_sub_text(sub)}\n🔗 <code>{sub.subscription_url}</code>"
        )


@router.message(F.text == texts.BTN_RENEW)
async def renew_list(message: Message, db: AsyncSession, user: User) -> None:
    subs = await subscription_service.list_for_user(db, user.id, only_active=True)
    if not subs:
        await message.answer(texts.NO_ACTIVE_SUBS)
        return
    for sub in subs:
        await message.answer(
            _sub_text(sub), reply_markup=keyboards.renew_kb(sub.id, sub.plan_id)
        )


@router.callback_query(F.data.startswith("renew:do:"))
async def renew_do(callback: CallbackQuery, db: AsyncSession, bot: Bot) -> None:
    _, _, sub_id, plan_id = callback.data.split(":")
    try:
        order, _ = await subscription_service.build_renewal_order(
            db, subscription_id=int(sub_id), plan_id=int(plan_id)
        )
        new_sub = await order_service.pay_with_wallet(db, order)
    except InsufficientBalanceError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    await callback.message.edit_text("✅ تمدید با موفقیت انجام شد.")
    await delivery.deliver_subscription(bot, callback.from_user.id, db, new_sub)
    await callback.answer()
