"""Subscription queries and renewal entry point."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.enums import OrderKind, SubscriptionStatus
from app.models.order import Subscription
from app.services import order_service, plan_service


async def list_for_user(
    db: AsyncSession, user_id: int, *, only_active: bool = False
) -> list[Subscription]:
    stmt = select(Subscription).where(Subscription.user_id == user_id)
    if only_active:
        stmt = stmt.where(Subscription.status == SubscriptionStatus.active)
    stmt = stmt.order_by(Subscription.expires_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_or_404(db: AsyncSession, subscription_id: int) -> Subscription:
    sub = await db.get(Subscription, subscription_id)
    if sub is None:
        raise NotFoundError(user_message="اشتراک یافت نشد.")
    return sub


async def build_renewal_order(
    db: AsyncSession, *, subscription_id: int, plan_id: int | None = None, coupon_code: str | None = None
):
    """Create a renewal order for an existing subscription (same plan by default)."""
    sub = await get_or_404(db, subscription_id)
    plan = await plan_service.get_or_404(db, plan_id or sub.plan_id)
    return await order_service.create_order(
        db,
        user_id=sub.user_id,
        plan=plan,
        kind=OrderKind.renewal,
        coupon_code=coupon_code,
        renew_subscription_id=sub.id,
    )
