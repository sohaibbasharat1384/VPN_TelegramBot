"""Wallet service — atomic credit/debit with a balance ledger.

All mutations lock the wallet row (`SELECT ... FOR UPDATE`) so concurrent
purchases and top-ups can't race the balance. Amounts are integer Toman.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientBalanceError, ValidationError
from app.models.enums import WalletTxnType
from app.models.user import Wallet, WalletTransaction


async def get_or_create_wallet(db: AsyncSession, user_id: int) -> Wallet:
    wallet = (
        await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    ).scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def get_balance(db: AsyncSession, user_id: int) -> int:
    wallet = await get_or_create_wallet(db, user_id)
    return wallet.balance


async def _locked_wallet(db: AsyncSession, user_id: int) -> Wallet:
    await get_or_create_wallet(db, user_id)  # ensure it exists
    return (
        await db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
    ).scalar_one()


async def credit(
    db: AsyncSession,
    user_id: int,
    amount: int,
    *,
    type: WalletTxnType,
    description: str = "",
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> WalletTransaction:
    if amount <= 0:
        raise ValidationError(user_message="مبلغ باید بزرگ‌تر از صفر باشد.")
    wallet = await _locked_wallet(db, user_id)
    wallet.balance += amount
    wallet.updated_at = datetime.now(UTC)
    txn = WalletTransaction(
        wallet_id=wallet.id,
        amount=amount,
        balance_after=wallet.balance,
        type=type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )
    db.add(txn)
    await db.flush()
    return txn


async def debit(
    db: AsyncSession,
    user_id: int,
    amount: int,
    *,
    type: WalletTxnType,
    description: str = "",
    reference_type: str | None = None,
    reference_id: int | None = None,
) -> WalletTransaction:
    if amount <= 0:
        raise ValidationError(user_message="مبلغ باید بزرگ‌تر از صفر باشد.")
    wallet = await _locked_wallet(db, user_id)
    if wallet.balance < amount:
        raise InsufficientBalanceError()
    wallet.balance -= amount
    wallet.updated_at = datetime.now(UTC)
    txn = WalletTransaction(
        wallet_id=wallet.id,
        amount=-amount,
        balance_after=wallet.balance,
        type=type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )
    db.add(txn)
    await db.flush()
    return txn


async def adjust(
    db: AsyncSession, user_id: int, delta: int, *, description: str
) -> WalletTransaction:
    """Admin manual adjustment (can be positive or negative)."""
    if delta >= 0:
        return await credit(
            db, user_id, delta, type=WalletTxnType.admin_adjust, description=description
        )
    return await debit(
        db, user_id, -delta, type=WalletTxnType.admin_adjust, description=description
    )


async def history(
    db: AsyncSession, user_id: int, *, limit: int = 20, offset: int = 0
) -> list[WalletTransaction]:
    wallet = await get_or_create_wallet(db, user_id)
    rows = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows.scalars().all())
