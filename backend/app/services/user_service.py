"""Customer (Telegram user) service: provisioning, search, ban/unban."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User, Wallet
from app.utils.codes import random_code


async def _unique_referral_code(db: AsyncSession) -> str:
    for _ in range(10):
        code = random_code(8)
        exists = (
            await db.execute(select(User.id).where(User.referral_code == code))
        ).scalar_one_or_none()
        if exists is None:
            return code
    raise RuntimeError("could not allocate a unique referral code")


async def get_by_telegram_id(db: AsyncSession, telegram_id: int) -> User | None:
    return (
        await db.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()


async def get_by_referral_code(db: AsyncSession, code: str) -> User | None:
    return (
        await db.execute(select(User).where(User.referral_code == code))
    ).scalar_one_or_none()


async def get_or_create(
    db: AsyncSession,
    *,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    referred_by_code: str | None = None,
) -> tuple[User, bool]:
    """Return (user, created). Links referrer + creates wallet on first contact."""
    user = await get_by_telegram_id(db, telegram_id)
    if user is not None:
        changed = False
        for attr, val in (("username", username), ("first_name", first_name), ("last_name", last_name)):
            if val is not None and getattr(user, attr) != val:
                setattr(user, attr, val)
                changed = True
        if changed:
            await db.flush()
        return user, False

    referred_by_id: int | None = None
    if referred_by_code:
        referrer = await get_by_referral_code(db, referred_by_code)
        if referrer and referrer.telegram_id != telegram_id:
            referred_by_id = referrer.id

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        referral_code=await _unique_referral_code(db),
        referred_by_id=referred_by_id,
    )
    db.add(user)
    await db.flush()
    db.add(Wallet(user_id=user.id, balance=0))
    await db.flush()
    return user, True


async def get_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError(user_message="کاربر یافت نشد.")
    return user


async def set_banned(db: AsyncSession, user_id: int, banned: bool, *, reason: str | None = None) -> User:
    user = await get_or_404(db, user_id)
    user.is_banned = banned
    user.banned_reason = reason if banned else None
    await db.flush()
    return user


async def search(
    db: AsyncSession, *, query: str | None = None, banned: bool | None = None,
    limit: int = 20, offset: int = 0,
) -> tuple[list[User], int]:
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if query:
        like = f"%{query}%"
        cond = or_(
            User.username.ilike(like),
            User.first_name.ilike(like),
            User.last_name.ilike(like),
            User.referral_code.ilike(like),
        )
        if query.lstrip("-").isdigit():
            cond = or_(cond, User.telegram_id == int(query))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if banned is not None:
        stmt = stmt.where(User.is_banned == banned)
        count_stmt = count_stmt.where(User.is_banned == banned)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(
        stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), total
