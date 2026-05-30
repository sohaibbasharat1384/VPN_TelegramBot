"""New-subscription purchase flow: plan selection, coupons, and payment."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import delivery, texts
from app.bot.customer import keyboards
from app.bot.customer.states import CardOrderFlow, CouponFlow
from app.core.config import settings
from app.core.exceptions import CouponError, DomainError, InsufficientBalanceError, OutOfStockError
from app.models.user import User
from app.services import (
    admin_service,
    coupon_service,
    order_service,
    payment_service,
    plan_service,
    settings_service,
)
from app.utils.formatting import gb, toman

router = Router()


async def _show_plans(message: Message, db: AsyncSession) -> None:
    plans = await plan_service.list_active(db)
    if not plans:
        await message.answer(texts.NO_PLANS)
        return
    await message.answer(texts.CHOOSE_PLAN, reply_markup=keyboards.plans_kb(plans))


@router.message(F.text == texts.BTN_BUY)
async def buy_entry(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await state.update_data(coupon=None)
    await _show_plans(message, db)


@router.callback_query(F.data == "buy:list")
async def buy_list(callback: CallbackQuery, db: AsyncSession) -> None:
    plans = await plan_service.list_active(db)
    await callback.message.edit_text(texts.CHOOSE_PLAN, reply_markup=keyboards.plans_kb(plans))
    await callback.answer()


async def _render_plan(
    callback: CallbackQuery, db: AsyncSession, user: User, plan_id: int, coupon: str | None
):
    plan = await plan_service.get_or_404(db, plan_id)
    try:
        pricing = await order_service.price(db, plan, user_id=user.id, coupon_code=coupon)
        price_text = toman(pricing.final_price)
        if pricing.discount_amount:
            price_text = f"<s>{toman(pricing.original_price)}</s> → {toman(pricing.final_price)}"
    except CouponError:
        coupon = None
        pricing = await order_service.price(db, plan, user_id=user.id)
        price_text = toman(pricing.final_price)

    gateway_enabled = await settings_service.get_bool(db, "gateway_enabled", False)
    text = texts.PLAN_DETAIL.format(
        title=plan.title, volume=gb(plan.data_limit_gb), days=plan.duration_days, price=price_text
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.payment_methods_kb(
            plan_id, has_coupon=bool(coupon), gateway_enabled=gateway_enabled
        ),
    )


@router.callback_query(F.data.startswith("buy:plan:"))
async def buy_plan(callback: CallbackQuery, db: AsyncSession, user: User, state: FSMContext) -> None:
    plan_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    await _render_plan(callback, db, user, plan_id, data.get("coupon"))
    await callback.answer()


@router.callback_query(F.data.startswith("buy:coupon:"))
async def buy_coupon(callback: CallbackQuery, db: AsyncSession, user: User, state: FSMContext) -> None:
    plan_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    if data.get("coupon"):
        await state.update_data(coupon=None)
        await _render_plan(callback, db, user, plan_id, None)
        await callback.answer(texts.COUPON_CLEARED)
        return
    await state.update_data(coupon_plan=plan_id)
    await state.set_state(CouponFlow.code)
    await callback.message.answer(texts.ENTER_COUPON)
    await callback.answer()


@router.message(CouponFlow.code)
async def coupon_received(message: Message, db: AsyncSession, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    plan_id = data.get("coupon_plan")
    plan = await plan_service.get_or_404(db, plan_id)
    try:
        _, discount = await coupon_service.validate_for(db, message.text.strip(), user.id, plan.price)
    except CouponError as exc:
        await message.answer(exc.user_message)
        return
    await state.update_data(coupon=message.text.strip().upper())
    await state.set_state(None)
    plans = await plan_service.list_active(db)
    await message.answer(texts.COUPON_APPLIED.format(discount=toman(discount)))
    await message.answer(texts.CHOOSE_PLAN, reply_markup=keyboards.plans_kb(plans))


# ---------------------------------------------------------------- payment ----
@router.callback_query(F.data.startswith("buy:pay:wallet:"))
async def pay_wallet(
    callback: CallbackQuery, db: AsyncSession, user: User, state: FSMContext, bot: Bot
) -> None:
    plan_id = int(callback.data.split(":")[3])
    plan = await plan_service.get_or_404(db, plan_id)
    coupon = (await state.get_data()).get("coupon")
    try:
        order, _ = await order_service.create_order(db, user_id=user.id, plan=plan, coupon_code=coupon)
        sub = await order_service.pay_with_wallet(db, order)
    except InsufficientBalanceError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    except OutOfStockError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    await state.update_data(coupon=None)
    await callback.message.edit_text("✅ پرداخت انجام شد.")
    await delivery.deliver_subscription(bot, callback.from_user.id, db, sub)
    await callback.answer()


@router.callback_query(F.data.startswith("buy:pay:gateway:"))
async def pay_gateway(callback: CallbackQuery, db: AsyncSession, user: User, state: FSMContext) -> None:
    plan_id = int(callback.data.split(":")[3])
    plan = await plan_service.get_or_404(db, plan_id)
    coupon = (await state.get_data()).get("coupon")
    try:
        order, _ = await order_service.create_order(db, user_id=user.id, plan=plan, coupon_code=coupon)
        _, url = await payment_service.create_gateway_order_payment(
            db, order=order, callback_url=settings.payment_callback_url
        )
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    await callback.message.edit_text(texts.GATEWAY_REDIRECT, reply_markup=keyboards.pay_now_kb(url))
    await callback.answer()


@router.callback_query(F.data.startswith("buy:pay:card:"))
async def pay_card(callback: CallbackQuery, db: AsyncSession, user: User, state: FSMContext) -> None:
    plan_id = int(callback.data.split(":")[3])
    plan = await plan_service.get_or_404(db, plan_id)
    coupon = (await state.get_data()).get("coupon")
    cards = await payment_service.active_cards(db)
    if not cards:
        await callback.answer(texts.NO_CARD, show_alert=True)
        return
    try:
        order, pricing = await order_service.create_order(
            db, user_id=user.id, plan=plan, coupon_code=coupon
        )
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    card = cards[0]
    await state.update_data(card_order_id=order.id, card_id=card.id, coupon=None)
    await state.set_state(CardOrderFlow.tracking)
    await callback.message.edit_text(
        texts.CARD_INFO.format(
            amount=toman(pricing.final_price),
            card_number=card.card_number,
            card_holder=card.card_holder,
            bank_name=card.bank_name,
        )
    )
    await callback.message.answer(texts.ENTER_TRACKING)
    await callback.answer()


@router.message(CardOrderFlow.tracking)
async def card_order_tracking(message: Message, state: FSMContext) -> None:
    await state.update_data(tracking=message.text.strip())
    await state.set_state(CardOrderFlow.receipt)
    await message.answer(texts.SEND_RECEIPT)


@router.message(CardOrderFlow.receipt, F.photo)
async def card_order_receipt(message: Message, db: AsyncSession, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    order = await order_service.get_or_404(db, data["card_order_id"])
    receipt_ref = message.photo[-1].file_id
    await payment_service.create_card_order_payment(
        db, order=order, card_id=data.get("card_id"),
        receipt_path=receipt_ref, tracking_number=data.get("tracking"),
    )
    await state.clear()
    await message.answer(texts.TOPUP_SUBMITTED, reply_markup=keyboards.main_menu())
    await admin_service.notify_admins(
        db,
        f"🧾 پرداخت کارت‌به‌کارت جدید برای سفارش #{order.id}\n"
        f"کاربر: {user.display_name}\nمبلغ: {toman(order.final_price)}\n"
        f"پیگیری: {data.get('tracking')}",
    )
