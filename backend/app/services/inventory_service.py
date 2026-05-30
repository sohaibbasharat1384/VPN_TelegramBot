"""Manual-inventory service: add/list configs, reserve, release, mark sold.

Reservation uses `FOR UPDATE SKIP LOCKED` so two concurrent buyers never grab
the same config, and abandoned reservations expire after a TTL.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import OutOfStockError
from app.models.catalog import Config
from app.models.enums import ConfigStatus

RESERVATION_TTL = timedelta(minutes=15)


async def add_config(
    db: AsyncSession,
    *,
    plan_id: int,
    subscription_url: str,
    raw_config: str,
    remark: str | None = None,
) -> Config:
    config = Config(
        plan_id=plan_id,
        subscription_url=subscription_url,
        raw_config=raw_config,
        remark=remark,
        status=ConfigStatus.available,
    )
    db.add(config)
    await db.flush()
    return config


async def bulk_add(db: AsyncSession, plan_id: int, items: list[dict]) -> int:
    for item in items:
        db.add(
            Config(
                plan_id=plan_id,
                subscription_url=item["subscription_url"],
                raw_config=item["raw_config"],
                remark=item.get("remark"),
                status=ConfigStatus.available,
            )
        )
    await db.flush()
    return len(items)


async def available_count(db: AsyncSession, plan_id: int) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Config)
            .where(Config.plan_id == plan_id, Config.status == ConfigStatus.available)
        )
    ).scalar_one()


async def counts_by_plan(db: AsyncSession) -> dict[int, dict[str, int]]:
    rows = await db.execute(
        select(Config.plan_id, Config.status, func.count())
        .group_by(Config.plan_id, Config.status)
    )
    result: dict[int, dict[str, int]] = {}
    for plan_id, status, count in rows.all():
        result.setdefault(plan_id, {}).update({status.value: count})
    return result


async def reserve(db: AsyncSession, plan_id: int, order_id: int) -> Config:
    """Atomically reserve one available config for an order."""
    now = datetime.now(UTC)
    stmt = (
        select(Config)
        .where(Config.plan_id == plan_id, Config.status == ConfigStatus.available)
        .order_by(Config.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    config = (await db.execute(stmt)).scalar_one_or_none()
    if config is None:
        raise OutOfStockError()
    config.status = ConfigStatus.reserved
    config.reserved_order_id = order_id
    config.reserved_until = now + RESERVATION_TTL
    await db.flush()
    return config


async def release(db: AsyncSession, config_id: int) -> None:
    config = await db.get(Config, config_id)
    if config and config.status == ConfigStatus.reserved:
        config.status = ConfigStatus.available
        config.reserved_order_id = None
        config.reserved_until = None
        await db.flush()


async def mark_sold(db: AsyncSession, config_id: int, user_id: int) -> Config:
    config = await db.get(Config, config_id)
    if config is None or config.status == ConfigStatus.sold:
        raise OutOfStockError()
    config.status = ConfigStatus.sold
    config.sold_to_user_id = user_id
    config.sold_at = datetime.now(UTC)
    config.reserved_order_id = None
    config.reserved_until = None
    await db.flush()
    return config


async def release_expired_reservations(db: AsyncSession) -> int:
    """Free configs whose reservation TTL has elapsed (Celery housekeeping)."""
    now = datetime.now(UTC)
    rows = await db.execute(
        select(Config).where(
            Config.status == ConfigStatus.reserved, Config.reserved_until < now
        )
    )
    configs = list(rows.scalars().all())
    for config in configs:
        config.status = ConfigStatus.available
        config.reserved_order_id = None
        config.reserved_until = None
    await db.flush()
    return len(configs)
