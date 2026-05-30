"""Coupon validation, discount computation, and redemption."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CouponError, NotFoundError
from app.models.coupon import Coupon, CouponRedemption
from app.models.enums import DiscountType


async def get_by_code(db: AsyncSession, code: str) -> Coupon | None:
    return (
        await db.execute(select(Coupon).where(Coupon.code == code.strip().upper()))
    ).scalar_one_or_none()


def compute_discount(coupon: Coupon, amount: int) -> int:
    if coupon.discount_type == DiscountType.percent:
        discount = amount * coupon.discount_value // 100
    else:
        discount = coupon.discount_value
    return max(0, min(discount, amount))


async def validate_for(db: AsyncSession, code: str, user_id: int, amount: int) -> tuple[Coupon, int]:
    """Validate a coupon for a user+amount; return (coupon, discount). Raises CouponError."""
    coupon = await get_by_code(db, code)
    now = datetime.now(UTC)
    if coupon is None or not coupon.is_active:
        raise CouponError()
    if coupon.expires_at is not None and coupon.expires_at <= now:
        raise CouponError(user_message="کد تخفیف منقضی شده است.")
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        raise CouponError(user_message="ظرفیت استفاده از این کد به پایان رسیده است.")
    if amount < coupon.min_order_amount:
        raise CouponError(user_message="مبلغ سفارش برای این کد کافی نیست.")

    used_by_user = (
        await db.execute(
            select(func.count())
            .select_from(CouponRedemption)
            .where(CouponRedemption.coupon_id == coupon.id, CouponRedemption.user_id == user_id)
        )
    ).scalar_one()
    if used_by_user >= coupon.per_user_limit:
        raise CouponError(user_message="شما قبلاً از این کد استفاده کرده‌اید.")

    discount = compute_discount(coupon, amount)
    if discount <= 0:
        raise CouponError()
    return coupon, discount


async def redeem(
    db: AsyncSession, coupon: Coupon, user_id: int, order_id: int, discount_amount: int
) -> CouponRedemption:
    coupon.used_count += 1
    redemption = CouponRedemption(
        coupon_id=coupon.id,
        user_id=user_id,
        order_id=order_id,
        discount_amount=discount_amount,
    )
    db.add(redemption)
    await db.flush()
    return redemption


# ---- admin management ----
async def create(
    db: AsyncSession,
    *,
    code: str,
    discount_type: DiscountType,
    discount_value: int,
    max_uses: int | None = None,
    per_user_limit: int = 1,
    min_order_amount: int = 0,
    expires_at: datetime | None = None,
) -> Coupon:
    code = code.strip().upper()
    if await get_by_code(db, code) is not None:
        raise CouponError(user_message="این کد قبلاً ثبت شده است.")
    coupon = Coupon(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        max_uses=max_uses,
        per_user_limit=per_user_limit,
        min_order_amount=min_order_amount,
        expires_at=expires_at,
    )
    db.add(coupon)
    await db.flush()
    return coupon


async def get_or_404(db: AsyncSession, coupon_id: int) -> Coupon:
    coupon = await db.get(Coupon, coupon_id)
    if coupon is None:
        raise NotFoundError(user_message="کد تخفیف یافت نشد.")
    return coupon


async def set_active(db: AsyncSession, coupon_id: int, active: bool) -> Coupon:
    coupon = await get_or_404(db, coupon_id)
    coupon.is_active = active
    await db.flush()
    return coupon
