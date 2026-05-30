"""Admin user management: search, profile, ban/unban, wallet adjust."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.admin.states import UserSearch, WalletAdjust
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.services import audit, user_service, wallet
from app.utils.formatting import jalali, toman

router = Router()


@router.message(F.text == texts.BTN_USERS)
async def users_entry(message: Message, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.USERS_VIEW):
        return
    await state.set_state(UserSearch.query)
    await message.answer(texts.ENTER_USER_QUERY)


async def _show_profile(message: Message, db: AsyncSession, user) -> None:
    balance = await wallet.get_balance(db, user.id)
    status = "🚫 مسدود" if user.is_banned else "✅ فعال"
    await message.answer(
        texts.USER_PROFILE.format(
            name=user.display_name, tid=user.telegram_id, balance=toman(balance),
            ref=user.referral_code, status=status, joined=jalali(user.created_at),
        ),
        reply_markup=keyboards.user_actions_kb(user.id, banned=user.is_banned),
    )


@router.message(UserSearch.query)
async def user_search(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    users, _ = await user_service.search(db, query=message.text.strip(), limit=5)
    if not users:
        await message.answer(texts.NO_USER_FOUND)
        return
    for user in users:
        await _show_profile(message, db, user)


@router.callback_query(F.data.startswith("user:ban:"))
@router.callback_query(F.data.startswith("user:unban:"))
async def toggle_ban(callback: CallbackQuery, db: AsyncSession, admin: AdminUser, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.USERS_BAN):
        return
    _, action, user_id = callback.data.split(":")
    banned = action == "ban"
    await user_service.set_banned(db, int(user_id), banned, reason="admin via bot" if banned else None)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id,
        action="user.ban" if banned else "user.unban",
        target_type="user", target_id=int(user_id), new_value={"banned": banned},
    )
    await db.commit()
    await callback.answer(texts.DONE)
    user = await user_service.get_or_404(db, int(user_id))
    await callback.message.edit_reply_markup(
        reply_markup=keyboards.user_actions_kb(user.id, banned=user.is_banned)
    )


@router.callback_query(F.data.startswith("user:adjust:"))
async def adjust_start(callback: CallbackQuery, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.WALLET_ADJUST):
        return
    user_id = int(callback.data.split(":")[2])
    await state.update_data(adjust_user_id=user_id)
    await state.set_state(WalletAdjust.amount)
    await callback.message.answer(texts.ENTER_ADJUST)
    await callback.answer()


@router.message(WalletAdjust.amount)
async def adjust_amount(message: Message, db: AsyncSession, admin: AdminUser, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", "")
    try:
        delta = int(raw)
    except ValueError:
        await message.answer(texts.ENTER_ADJUST)
        return
    data = await state.get_data()
    user_id = data["adjust_user_id"]
    await state.clear()
    txn = await wallet.adjust(db, user_id, delta, description="تنظیم دستی توسط مدیر")
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="wallet.adjust",
        target_type="user", target_id=user_id,
        new_value={"delta": delta, "balance_after": txn.balance_after},
    )
    await db.commit()
    await message.answer(texts.ADJUST_DONE.format(balance=toman(txn.balance_after)))
