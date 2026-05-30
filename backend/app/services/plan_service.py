"""Plan catalog service (list/get + admin pricing CRUD)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.catalog import Plan
from app.models.enums import FulfilmentMode


async def list_active(db: AsyncSession) -> list[Plan]:
    rows = await db.execute(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order, Plan.price)
    )
    return list(rows.scalars().all())


async def list_all(db: AsyncSession) -> list[Plan]:
    rows = await db.execute(select(Plan).order_by(Plan.sort_order, Plan.price))
    return list(rows.scalars().all())


async def get_or_404(db: AsyncSession, plan_id: int) -> Plan:
    plan = await db.get(Plan, plan_id)
    if plan is None:
        raise NotFoundError(user_message="پلن یافت نشد.")
    return plan


async def create(
    db: AsyncSession,
    *,
    title: str,
    data_limit_gb: int,
    duration_days: int,
    price: int,
    fulfilment_mode: FulfilmentMode = FulfilmentMode.manual,
    panel_id: int | None = None,
    sort_order: int = 0,
) -> Plan:
    if fulfilment_mode == FulfilmentMode.panel and panel_id is None:
        raise ValidationError(user_message="برای حالت پنل، انتخاب پنل الزامی است.")
    plan = Plan(
        title=title,
        data_limit_gb=data_limit_gb,
        duration_days=duration_days,
        price=price,
        fulfilment_mode=fulfilment_mode,
        panel_id=panel_id,
        sort_order=sort_order,
    )
    db.add(plan)
    await db.flush()
    return plan


async def update(db: AsyncSession, plan_id: int, **fields: object) -> Plan:
    plan = await get_or_404(db, plan_id)
    allowed = {
        "title", "data_limit_gb", "duration_days", "price",
        "fulfilment_mode", "panel_id", "is_active", "sort_order",
    }
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(plan, key, value)
    if plan.fulfilment_mode == FulfilmentMode.panel and plan.panel_id is None:
        raise ValidationError(user_message="برای حالت پنل، انتخاب پنل الزامی است.")
    await db.flush()
    return plan
