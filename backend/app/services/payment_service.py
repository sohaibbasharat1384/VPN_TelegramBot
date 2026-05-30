"""Payment service: card-to-card top-ups/orders and admin approval flow.

Online-gateway request/verify lives in ``app.integrations.payments`` and is wired
through ``create_gateway_*`` in the payment-integration increment.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    WalletTxnType,
)
from app.models.order import Order, Payment, PaymentCard
from app.services import order_service, wallet


async def active_cards(db: AsyncSession) -> list[PaymentCard]:
    rows = await db.execute(
        select(PaymentCard).where(PaymentCard.is_active.is_(True)).order_by(PaymentCard.sort_order)
    )
    return list(rows.scalars().all())


async def create_card_topup(
    db: AsyncSession,
    *,
    user_id: int,
    amount: int,
    card_id: int | None,
    receipt_path: str | None,
    tracking_number: str | None,
) -> Payment:
    if amount <= 0:
        raise ValidationError(user_message="مبلغ نامعتبر است.")
    payment = Payment(
        user_id=user_id,
        order_id=None,
        purpose=PaymentPurpose.wallet_topup,
        method=PaymentMethod.card_to_card,
        amount=amount,
        status=PaymentStatus.pending,
        card_id=card_id,
        receipt_path=receipt_path,
        tracking_number=tracking_number,
    )
    db.add(payment)
    await db.flush()
    return payment


async def create_card_order_payment(
    db: AsyncSession,
    *,
    order: Order,
    card_id: int | None,
    receipt_path: str | None,
    tracking_number: str | None,
) -> Payment:
    payment = Payment(
        user_id=order.user_id,
        order_id=order.id,
        purpose=PaymentPurpose.order,
        method=PaymentMethod.card_to_card,
        amount=order.final_price,
        status=PaymentStatus.pending,
        card_id=card_id,
        receipt_path=receipt_path,
        tracking_number=tracking_number,
    )
    db.add(payment)
    await db.flush()
    return payment


async def get_or_404(db: AsyncSession, payment_id: int) -> Payment:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise NotFoundError(user_message="پرداخت یافت نشد.")
    return payment


async def approve(db: AsyncSession, payment: Payment, *, admin_id: int, note: str | None = None):
    """Approve a pending payment: credit wallet (top-up) or fulfil order."""
    if payment.status != PaymentStatus.pending:
        raise ValidationError(user_message="این پرداخت قبلاً بررسی شده است.")
    payment.status = PaymentStatus.approved
    payment.reviewed_by_id = admin_id
    payment.admin_note = note

    result = None
    if payment.purpose == PaymentPurpose.wallet_topup:
        await wallet.credit(
            db,
            payment.user_id,
            payment.amount,
            type=WalletTxnType.topup,
            description="شارژ کیف پول (کارت به کارت)",
            reference_type="payment",
            reference_id=payment.id,
        )
    else:  # order payment
        order = await db.get(Order, payment.order_id)
        if order is None:
            raise NotFoundError(user_message="سفارش مرتبط یافت نشد.")
        result = await order_service.settle_paid_order(db, order)
    await db.flush()
    return result


async def reject(db: AsyncSession, payment: Payment, *, admin_id: int, note: str | None = None) -> None:
    if payment.status != PaymentStatus.pending:
        raise ValidationError(user_message="این پرداخت قبلاً بررسی شده است.")
    payment.status = PaymentStatus.rejected
    payment.reviewed_by_id = admin_id
    payment.admin_note = note
    # Release inventory held by a rejected card-to-card order payment.
    if payment.purpose == PaymentPurpose.order and payment.order_id:
        order = await db.get(Order, payment.order_id)
        if order is not None:
            await order_service.cancel(db, order)
    await db.flush()


async def list_payments(
    db: AsyncSession,
    *,
    status: PaymentStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Payment], int]:
    stmt = select(Payment)
    count_stmt = select(func.count()).select_from(Payment)
    if status is not None:
        stmt = stmt.where(Payment.status == status)
        count_stmt = count_stmt.where(Payment.status == status)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(
        stmt.order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), total


async def pending_count(db: AsyncSession) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.pending)
        )
    ).scalar_one()


# --------------------------------------------------------------------------- #
# Online payment gateway flows (ZarinPal / IDPay / NextPay)
# --------------------------------------------------------------------------- #
async def _create_gateway_payment(
    db: AsyncSession,
    *,
    user_id: int,
    amount: int,
    purpose: PaymentPurpose,
    order_id: int | None,
    callback_url: str,
    description: str,
    mobile: str | None = None,
) -> tuple[Payment, str]:
    from app.integrations.payments.factory import get_gateway

    gateway = get_gateway()
    payment = Payment(
        user_id=user_id,
        order_id=order_id,
        purpose=purpose,
        method=PaymentMethod.gateway,
        provider=gateway.name,
        amount=amount,
        status=PaymentStatus.pending,
    )
    db.add(payment)
    await db.flush()
    result = await gateway.request(
        amount_toman=amount,
        callback_url=callback_url,
        description=description,
        order_id=str(payment.id),
        mobile=mobile,
    )
    payment.gateway_authority = result.authority
    await db.flush()
    return payment, result.redirect_url


async def create_gateway_topup(
    db: AsyncSession, *, user_id: int, amount: int, callback_url: str, mobile: str | None = None
) -> tuple[Payment, str]:
    if amount <= 0:
        raise ValidationError(user_message="مبلغ نامعتبر است.")
    return await _create_gateway_payment(
        db, user_id=user_id, amount=amount, purpose=PaymentPurpose.wallet_topup,
        order_id=None, callback_url=callback_url, description="شارژ کیف پول", mobile=mobile,
    )


async def create_gateway_order_payment(
    db: AsyncSession, *, order: Order, callback_url: str, mobile: str | None = None
) -> tuple[Payment, str]:
    return await _create_gateway_payment(
        db, user_id=order.user_id, amount=order.final_price, purpose=PaymentPurpose.order,
        order_id=order.id, callback_url=callback_url,
        description=f"پرداخت سفارش #{order.id}", mobile=mobile,
    )


async def verify_and_settle(db: AsyncSession, authority: str):
    """Verify a gateway payment by its authority and settle it. Idempotent."""
    from app.integrations.payments.factory import get_gateway

    payment = (
        await db.execute(select(Payment).where(Payment.gateway_authority == authority))
    ).scalar_one_or_none()
    if payment is None:
        raise NotFoundError(user_message="پرداخت یافت نشد.")
    if payment.status == PaymentStatus.approved:
        return payment, True  # already settled

    gateway = get_gateway(payment.provider)
    verify = await gateway.verify(
        authority=authority, amount_toman=payment.amount, order_id=str(payment.id)
    )
    if not verify.success:
        payment.status = PaymentStatus.failed
        await db.flush()
        return payment, False

    payment.status = PaymentStatus.approved
    payment.gateway_ref_id = verify.ref_id
    if payment.purpose == PaymentPurpose.wallet_topup:
        await wallet.credit(
            db, payment.user_id, payment.amount, type=WalletTxnType.topup,
            description="شارژ کیف پول (درگاه پرداخت)",
            reference_type="payment", reference_id=payment.id,
        )
    else:
        order = await db.get(Order, payment.order_id)
        if order is not None and order.status != OrderStatus.delivered:
            await order_service.settle_paid_order(db, order)
    await db.flush()
    return payment, True


def _now() -> datetime:
    return datetime.now(UTC)
