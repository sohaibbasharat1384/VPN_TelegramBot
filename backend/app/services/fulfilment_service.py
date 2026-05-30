"""Fulfilment strategies — turn a paid order into a delivered subscription.

Two modes, chosen per-plan:
  * manual : consume the inventory config reserved for the order.
  * panel  : provision the user on the configured panel (Marzban / X-UI).

The panel branch delegates to ``app.integrations.panels`` (implemented in the
panel-integration increment); it is imported lazily so manual-only deployments
need no panel configuration.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import OutOfStockError, PanelIntegrationError
from app.models.catalog import Config, Plan
from app.models.enums import ConfigStatus, FulfilmentMode, OrderStatus, SubscriptionStatus
from app.models.order import Order, Subscription
from app.services import inventory_service


async def _deliver_manual(db: AsyncSession, order: Order, plan: Plan) -> Subscription:
    config = (
        await db.execute(
            select(Config).where(
                Config.reserved_order_id == order.id, Config.status == ConfigStatus.reserved
            )
        )
    ).scalar_one_or_none()
    if config is None:
        # Reservation expired/lost — try to grab a fresh one before failing.
        config = await inventory_service.reserve(db, plan.id, order.id)
    await inventory_service.mark_sold(db, config.id, order.user_id)

    now = datetime.now(UTC)
    sub = Subscription(
        user_id=order.user_id,
        plan_id=plan.id,
        order_id=order.id,
        config_id=config.id,
        panel_id=None,
        subscription_url=config.subscription_url,
        data_limit_bytes=plan.data_limit_bytes,
        starts_at=now,
        expires_at=now + timedelta(days=plan.duration_days),
        status=SubscriptionStatus.active,
    )
    db.add(sub)
    await db.flush()
    return sub


async def _deliver_panel(db: AsyncSession, order: Order, plan: Plan) -> Subscription:
    if plan.panel_id is None:
        raise PanelIntegrationError("plan has no panel configured")
    # Lazy import keeps the panel SDK optional for manual-only installs.
    from app.integrations.panels import provision_subscription

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=plan.duration_days)
    result = await provision_subscription(
        db,
        panel_id=plan.panel_id,
        user_id=order.user_id,
        data_limit_bytes=plan.data_limit_bytes,
        expires_at=expires_at,
        renew_subscription_id=order.renew_subscription_id,
    )
    sub = Subscription(
        user_id=order.user_id,
        plan_id=plan.id,
        order_id=order.id,
        config_id=None,
        panel_id=plan.panel_id,
        panel_username=result.username,
        subscription_url=result.subscription_url,
        data_limit_bytes=plan.data_limit_bytes,
        starts_at=now,
        expires_at=expires_at,
        status=SubscriptionStatus.active,
    )
    db.add(sub)
    await db.flush()
    return sub


async def deliver(db: AsyncSession, order: Order) -> Subscription:
    """Create the subscription for a paid order. Idempotent per order."""
    existing = (
        await db.execute(select(Subscription).where(Subscription.order_id == order.id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    plan = await db.get(Plan, order.plan_id)
    if plan is None:
        raise OutOfStockError()

    if plan.fulfilment_mode == FulfilmentMode.manual:
        sub = await _deliver_manual(db, order, plan)
    else:
        sub = await _deliver_panel(db, order, plan)

    # If this is a renewal, retire the previous subscription.
    if order.renew_subscription_id:
        old = await db.get(Subscription, order.renew_subscription_id)
        if old is not None and old.id != sub.id:
            old.status = SubscriptionStatus.disabled

    order.status = OrderStatus.delivered
    await db.flush()
    return sub
