"""Order pricing, creation (with inventory reservation), and wallet checkout."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.catalog import Plan
from app.models.coupon import Coupon
from app.models.enums import (
    FulfilmentMode,
    OrderKind,
    OrderStatus,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    WalletTxnType,
)
from app.models.order import Order, Payment, Subscription
from app.services import (
    coupon_service,
    fulfilment_service,
    inventory_service,
    referral_service,
    wallet,
)


@dataclass(slots=True)
class Pricing:
    original_price: int
    discount_amount: int
    final_price: int
    coupon: Coupon | None


async def price(
    db: AsyncSession, plan: Plan, *, user_id: int, coupon_code: str | None = None
) -> Pricing:
    original = plan.price
    discount = 0
    coupon: Coupon | None = None
    if coupon_code:
        coupon, discount = await coupon_service.validate_for(db, coupon_code, user_id, original)
    return Pricing(original, discount, original - discount, coupon)


async def create_order(
    db: AsyncSession,
    *,
    user_id: int,
    plan: Plan,
    kind: OrderKind = OrderKind.new,
    coupon_code: str | None = None,
    renew_subscription_id: int | None = None,
) -> tuple[Order, Pricing]:
    """Create an order in `awaiting_payment` and reserve inventory if manual."""
    pricing = await price(db, plan, user_id=user_id, coupon_code=coupon_code)

    order = Order(
        user_id=user_id,
        plan_id=plan.id,
        kind=kind,
        renew_subscription_id=renew_subscription_id,
        original_price=pricing.original_price,
        coupon_id=pricing.coupon.id if pricing.coupon else None,
        discount_amount=pricing.discount_amount,
        final_price=pricing.final_price,
        status=OrderStatus.pending,
    )
    db.add(order)
    await db.flush()

    # Hold stock immediately for manual plans (raises OutOfStock if none).
    if plan.fulfilment_mode == FulfilmentMode.manual:
        await inventory_service.reserve(db, plan.id, order.id)

    order.status = OrderStatus.awaiting_payment
    await db.flush()
    return order, pricing


async def _on_paid(db: AsyncSession, order: Order) -> Subscription:
    """Common post-payment path: redeem coupon, deliver, trigger referral reward."""
    order.status = OrderStatus.paid
    if order.coupon_id:
        coupon = await db.get(Coupon, order.coupon_id)
        if coupon is not None:
            await coupon_service.redeem(db, coupon, order.user_id, order.id, order.discount_amount)
    sub = await fulfilment_service.deliver(db, order)
    await referral_service.on_qualifying_purchase(db, order.user_id)
    return sub


async def pay_with_wallet(db: AsyncSession, order: Order) -> Subscription:
    """Charge the user's wallet and fulfil immediately."""
    if order.status not in (OrderStatus.awaiting_payment, OrderStatus.pending):
        raise ValidationError(user_message="این سفارش قابل پرداخت نیست.")

    await wallet.debit(
        db,
        order.user_id,
        order.final_price,
        type=WalletTxnType.purchase,
        description=f"خرید سفارش #{order.id}",
        reference_type="order",
        reference_id=order.id,
    )
    db.add(
        Payment(
            user_id=order.user_id,
            order_id=order.id,
            purpose=PaymentPurpose.order,
            method=PaymentMethod.wallet,
            amount=order.final_price,
            status=PaymentStatus.approved,
        )
    )
    sub = await _on_paid(db, order)
    await db.commit()
    return sub


async def settle_paid_order(db: AsyncSession, order: Order) -> Subscription:
    """Fulfil an order whose external payment (card/gateway) was just approved."""
    return await _on_paid(db, order)


async def get_or_404(db: AsyncSession, order_id: int) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise NotFoundError(user_message="سفارش یافت نشد.")
    return order


async def cancel(db: AsyncSession, order: Order) -> None:
    """Cancel an unpaid order and release any reserved inventory."""
    if order.status in (OrderStatus.delivered, OrderStatus.paid):
        raise ValidationError(user_message="سفارش پرداخت‌شده قابل لغو نیست.")
    from app.models.catalog import Config

    config = (
        await db.execute(select(Config).where(Config.reserved_order_id == order.id))
    ).scalar_one_or_none()
    if config is not None:
        await inventory_service.release(db, config.id)
    order.status = OrderStatus.cancelled
    await db.flush()


# Orders left awaiting payment longer than this are auto-expired (Celery).
STALE_ORDER_TTL = timedelta(minutes=30)


async def expire_stale_orders(db: AsyncSession) -> int:
    """Expire abandoned awaiting-payment orders and release their inventory."""
    cutoff = datetime.now(UTC) - STALE_ORDER_TTL
    rows = await db.execute(
        select(Order).where(
            Order.status == OrderStatus.awaiting_payment, Order.created_at < cutoff
        )
    )
    count = 0
    for order in rows.scalars().all():
        await cancel(db, order)
        order.status = OrderStatus.expired
        count += 1
    await db.flush()
    return count
