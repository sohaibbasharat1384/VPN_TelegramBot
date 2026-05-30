"""Aggregated statistics for the dashboard overview and admin bot."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus, SubscriptionStatus
from app.models.order import Payment, Subscription
from app.models.referral import ReferralReward
from app.models.user import User, Wallet


async def _revenue_since(db: AsyncSession, since: datetime) -> int:
    val = (
        await db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.status == PaymentStatus.approved, Payment.created_at >= since
            )
        )
    ).scalar_one()
    return int(val)


async def overview(db: AsyncSession) -> dict:
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    daily_users = (
        await db.execute(select(func.count()).select_from(User).where(User.created_at >= day_ago))
    ).scalar_one()
    active_subs = (
        await db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == SubscriptionStatus.active)
        )
    ).scalar_one()
    # "Active users" = users with at least one active subscription.
    active_users = (
        await db.execute(
            select(func.count(func.distinct(Subscription.user_id))).where(
                Subscription.status == SubscriptionStatus.active
            )
        )
    ).scalar_one()
    wallet_total = (
        await db.execute(select(func.coalesce(func.sum(Wallet.balance), 0)))
    ).scalar_one()
    referral_total = (
        await db.execute(select(func.coalesce(func.sum(ReferralReward.amount), 0)))
    ).scalar_one()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "daily_users": daily_users,
        "active_subscriptions": active_subs,
        "revenue_daily": await _revenue_since(db, day_ago),
        "revenue_weekly": await _revenue_since(db, week_ago),
        "revenue_monthly": await _revenue_since(db, month_ago),
        "wallet_total": int(wallet_total),
        "referral_total": int(referral_total),
    }


async def revenue_series(db: AsyncSession, *, days: int = 14) -> list[dict]:
    """Daily approved-payment totals for the last `days` days (for charts)."""
    since = datetime.now(UTC) - timedelta(days=days)
    rows = await db.execute(
        select(
            func.date_trunc("day", Payment.created_at).label("day"),
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
        )
        .where(Payment.status == PaymentStatus.approved, Payment.created_at >= since)
        .group_by("day")
        .order_by("day")
    )
    return [{"date": r.day.date().isoformat(), "total": int(r.total)} for r in rows.all()]
