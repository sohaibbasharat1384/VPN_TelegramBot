"""Referral tracking and reward granting.

A referral is created when an invited user first contacts the bot. When the
referred user completes their first qualifying purchase, the referrer is credited
from `settings.referral_reward_amount`.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReferralStatus, WalletTxnType
from app.models.referral import Referral, ReferralReward
from app.models.user import User
from app.services import settings_service, wallet


async def ensure_referral(db: AsyncSession, user: User) -> Referral | None:
    """Create the referral record for a newly-registered referred user."""
    if user.referred_by_id is None:
        return None
    existing = (
        await db.execute(select(Referral).where(Referral.referred_id == user.id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    referral = Referral(
        referrer_id=user.referred_by_id,
        referred_id=user.id,
        status=ReferralStatus.pending,
    )
    db.add(referral)
    await db.flush()
    return referral


async def on_qualifying_purchase(db: AsyncSession, referred_user_id: int) -> ReferralReward | None:
    """Grant the referrer their reward once, on the referred user's first purchase."""
    referral = (
        await db.execute(select(Referral).where(Referral.referred_id == referred_user_id))
    ).scalar_one_or_none()
    if referral is None or referral.status == ReferralStatus.rewarded:
        return None

    reward_amount = await settings_service.get_int(db, "referral_reward_amount", 0)
    referral.status = ReferralStatus.rewarded
    if reward_amount <= 0:
        await db.flush()
        return None

    txn = await wallet.credit(
        db,
        referral.referrer_id,
        reward_amount,
        type=WalletTxnType.referral_reward,
        description="پاداش معرفی دوست",
        reference_type="referral",
        reference_id=referral.id,
    )
    reward = ReferralReward(
        referral_id=referral.id,
        referrer_id=referral.referrer_id,
        amount=reward_amount,
        wallet_transaction_id=txn.id,
    )
    db.add(reward)
    await db.flush()
    return reward


async def stats_for(db: AsyncSession, user_id: int) -> dict[str, int]:
    total = (
        await db.execute(
            select(func.count()).select_from(Referral).where(Referral.referrer_id == user_id)
        )
    ).scalar_one()
    rewarded = (
        await db.execute(
            select(func.count())
            .select_from(Referral)
            .where(Referral.referrer_id == user_id, Referral.status == ReferralStatus.rewarded)
        )
    ).scalar_one()
    earned = (
        await db.execute(
            select(func.coalesce(func.sum(ReferralReward.amount), 0)).where(
                ReferralReward.referrer_id == user_id
            )
        )
    ).scalar_one()
    return {"total": total, "rewarded": rewarded, "earned": int(earned)}
