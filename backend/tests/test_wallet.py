"""DB-backed tests for the wallet ledger and inventory reservation."""
from __future__ import annotations

import pytest

from app.core.exceptions import InsufficientBalanceError, OutOfStockError
from app.models.enums import FulfilmentMode, WalletTxnType
from app.services import inventory_service, plan_service, user_service, wallet


async def _make_user(db, tid: int):
    user, _ = await user_service.get_or_create(db, telegram_id=tid)
    await db.commit()
    return user


async def test_credit_and_debit(db):
    user = await _make_user(db, 1001)
    await wallet.credit(db, user.id, 50_000, type=WalletTxnType.topup, description="t")
    assert await wallet.get_balance(db, user.id) == 50_000

    txn = await wallet.debit(db, user.id, 20_000, type=WalletTxnType.purchase, description="p")
    assert txn.balance_after == 30_000
    assert await wallet.get_balance(db, user.id) == 30_000


async def test_overdraft_blocked(db):
    user = await _make_user(db, 1002)
    await wallet.credit(db, user.id, 10_000, type=WalletTxnType.topup, description="t")
    with pytest.raises(InsufficientBalanceError):
        await wallet.debit(db, user.id, 99_999, type=WalletTxnType.purchase, description="p")
    assert await wallet.get_balance(db, user.id) == 10_000


async def test_inventory_reserve_then_out_of_stock(db):
    plan = await plan_service.create(
        db, title="T", data_limit_gb=1, duration_days=30, price=1000,
        fulfilment_mode=FulfilmentMode.manual,
    )
    await inventory_service.add_config(
        db, plan_id=plan.id, subscription_url="vless://a", raw_config="vless://a"
    )
    await db.commit()

    assert await inventory_service.available_count(db, plan.id) == 1
    await inventory_service.reserve(db, plan.id, order_id=1)
    assert await inventory_service.available_count(db, plan.id) == 0
    with pytest.raises(OutOfStockError):
        await inventory_service.reserve(db, plan.id, order_id=2)
