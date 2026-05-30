"""Payment review: list pending, approve (+deliver), reject."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.common.delivery import deliver_subscription
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.permissions import Perm
from app.models.enums import ActorType, PaymentPurpose, PaymentStatus
from app.models.order import Subscription
from app.models.rbac import AdminUser
from app.models.user import User
from app.services import audit, payment_service
from app.utils.formatting import toman
from app.utils.telegram import send_message

router = Router()

_PURPOSE_FA = {PaymentPurpose.order: "خرید اشتراک", PaymentPurpose.wallet_topup: "شارژ کیف پول"}


@router.message(F.text == texts.BTN_PAYMENTS)
async def list_pending(message: Message, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.PAYMENTS_VIEW):
        return
    payments, _ = await payment_service.list_payments(db, status=PaymentStatus.pending, limit=20)
    if not payments:
        await message.answer(texts.NO_PENDING_PAYMENTS)
        return
    for p in payments:
        user = await db.get(User, p.user_id)
        text = texts.PAYMENT_CARD.format(
            id=p.id, user=user.display_name if user else p.user_id,
            purpose=_PURPOSE_FA.get(p.purpose, p.purpose.value),
            amount=toman(p.amount), tracking=p.tracking_number or "—",
        )
        if p.receipt_path:
            try:
                await message.answer_photo(p.receipt_path, caption=text,
                                           reply_markup=keyboards.review_kb(p.id))
                continue
            except Exception:  # noqa: BLE001 — receipt file_id may be stale
                pass
        await message.answer(text, reply_markup=keyboards.review_kb(p.id))


async def _deliver_to_customer(db: AsyncSession, sub: Subscription) -> None:
    user = await db.get(User, sub.user_id)
    if user is None:
        return
    bot = Bot(settings.customer_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await deliver_subscription(bot, user.telegram_id, db, sub)
    finally:
        await bot.session.close()


@router.callback_query(F.data.startswith("pay:approve:"))
async def approve(callback: CallbackQuery, db: AsyncSession, admin: AdminUser, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.PAYMENTS_APPROVE):
        return
    payment_id = int(callback.data.split(":")[2])
    payment = await payment_service.get_or_404(db, payment_id)
    try:
        result = await payment_service.approve(db, payment, admin_id=admin.id)
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="payment.approve",
        target_type="payment", target_id=payment_id, new_value={"amount": payment.amount},
    )
    await db.commit()

    if isinstance(result, Subscription):
        await _deliver_to_customer(db, result)
    else:
        user = await db.get(User, payment.user_id)
        if user:
            await send_message(
                settings.customer_bot_token, user.telegram_id,
                f"✅ کیف پول شما به مبلغ {toman(payment.amount)} شارژ شد.",
            )
    await callback.message.edit_text(texts.PAYMENT_APPROVED.format(id=payment_id))
    await callback.answer()


@router.callback_query(F.data.startswith("pay:reject:"))
async def reject(callback: CallbackQuery, db: AsyncSession, admin: AdminUser, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.PAYMENTS_APPROVE):
        return
    payment_id = int(callback.data.split(":")[2])
    payment = await payment_service.get_or_404(db, payment_id)
    try:
        await payment_service.reject(db, payment, admin_id=admin.id)
    except DomainError as exc:
        await callback.answer(exc.user_message, show_alert=True)
        return
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="payment.reject",
        target_type="payment", target_id=payment_id,
    )
    await db.commit()
    user = await db.get(User, payment.user_id)
    if user:
        reject_msg = (
            f"❌ پرداخت شما به مبلغ {toman(payment.amount)} تأیید نشد.\n"
            "در صورت کسر وجه با پشتیبانی تماس بگیرید."
        )
        await send_message(settings.customer_bot_token, user.telegram_id, reject_msg)
    await callback.message.edit_text(texts.PAYMENT_REJECTED.format(id=payment_id))
    await callback.answer()
