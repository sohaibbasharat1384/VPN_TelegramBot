"""Wallet: balance, history, and top-up (card-to-card / gateway)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import texts
from app.bot.customer import keyboards
from app.bot.customer.states import ChargeWallet
from app.core.config import settings
from app.core.exceptions import DomainError
from app.models.user import User
from app.services import admin_service, payment_service, settings_service, wallet
from app.utils.formatting import jalali, to_fa_digits, toman

router = Router()

_TXN_LABEL = {
    "topup": "شارژ",
    "purchase": "خرید",
    "refund": "بازگشت وجه",
    "referral_reward": "پاداش معرفی",
    "admin_adjust": "تنظیم مدیر",
}


@router.message(F.text == texts.BTN_WALLET)
async def wallet_menu(message: Message, db: AsyncSession, user: User) -> None:
    balance = await wallet.get_balance(db, user.id)
    await message.answer(
        texts.WALLET_INFO.format(balance=toman(balance)), reply_markup=keyboards.wallet_menu_kb()
    )


@router.callback_query(F.data == "wallet:history")
async def wallet_history(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    txns = await wallet.history(db, user.id, limit=15)
    if not txns:
        await callback.answer(texts.WALLET_EMPTY_HISTORY, show_alert=True)
        return
    lines = []
    for t in txns:
        sign = "➕" if t.amount > 0 else "➖"
        label = _TXN_LABEL.get(t.type.value, t.type.value)
        lines.append(f"{sign} {to_fa_digits(abs(t.amount)):>}  {label} — {jalali(t.created_at)}")
    await callback.message.answer("🧾 آخرین تراکنش‌ها:\n\n" + "\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "wallet:charge")
async def charge_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ChargeWallet.amount)
    await callback.message.answer(texts.ENTER_CHARGE_AMOUNT)
    await callback.answer()


@router.message(ChargeWallet.amount)
async def charge_amount(message: Message, db: AsyncSession, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", "").replace("،", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(texts.INVALID_AMOUNT)
        return
    amount = int(raw)
    await state.update_data(amount=amount)
    card_enabled = await settings_service.get_bool(db, "card_to_card_enabled", True)
    gateway_enabled = await settings_service.get_bool(db, "gateway_enabled", False)
    if not card_enabled and not gateway_enabled:
        await message.answer(texts.NO_CARD)
        await state.clear()
        return
    await message.answer(
        texts.CHOOSE_CHARGE_METHOD,
        reply_markup=keyboards.charge_methods_kb(
            card_enabled=card_enabled, gateway_enabled=gateway_enabled
        ),
    )


@router.callback_query(F.data == "wallet:charge:gateway")
async def charge_gateway(callback: CallbackQuery, db: AsyncSession, user: User, state: FSMContext) -> None:
    amount = (await state.get_data()).get("amount", 0)
    try:
        _, url = await payment_service.create_gateway_topup(
            db, user_id=user.id, amount=amount, callback_url=settings.payment_callback_url
        )
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(texts.GATEWAY_REDIRECT, reply_markup=keyboards.pay_now_kb(url))
    await callback.answer()


@router.callback_query(F.data == "wallet:charge:card")
async def charge_card(callback: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    amount = (await state.get_data()).get("amount", 0)
    cards = await payment_service.active_cards(db)
    if not cards:
        await callback.answer(texts.NO_CARD, show_alert=True)
        return
    card = cards[0]
    await state.update_data(card_id=card.id)
    await state.set_state(ChargeWallet.tracking)
    await callback.message.edit_text(
        texts.CARD_INFO.format(
            amount=toman(amount), card_number=card.card_number,
            card_holder=card.card_holder, bank_name=card.bank_name,
        )
    )
    await callback.message.answer(texts.ENTER_TRACKING)
    await callback.answer()


@router.message(ChargeWallet.tracking)
async def charge_tracking(message: Message, state: FSMContext) -> None:
    await state.update_data(tracking=message.text.strip())
    await state.set_state(ChargeWallet.receipt)
    await message.answer(texts.SEND_RECEIPT)


@router.message(ChargeWallet.receipt, F.photo)
async def charge_receipt(message: Message, db: AsyncSession, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    amount = data.get("amount", 0)
    await payment_service.create_card_topup(
        db, user_id=user.id, amount=amount, card_id=data.get("card_id"),
        receipt_path=message.photo[-1].file_id, tracking_number=data.get("tracking"),
    )
    await state.clear()
    await message.answer(texts.TOPUP_SUBMITTED, reply_markup=keyboards.main_menu())
    await admin_service.notify_admins(
        db,
        f"💰 درخواست شارژ کیف پول\nکاربر: {user.display_name}\n"
        f"مبلغ: {toman(amount)}\nپیگیری: {data.get('tracking')}",
    )
