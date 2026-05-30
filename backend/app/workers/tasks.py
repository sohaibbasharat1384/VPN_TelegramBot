"""Celery tasks.

Celery is synchronous, so each task runs its async body via ``asyncio.run`` inside
a dedicated transactional session scope. Tasks are intentionally thin — the real
work lives in services so it stays unit-testable and shared with the API/bots.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.logging import get_logger
from app.db.session import session_scope
from app.services import alerts_service, inventory_service, order_service
from app.workers.celery_app import celery_app

logger = get_logger("worker")
T = TypeVar("T")


def _run(coro_factory: Callable[..., Awaitable[T]]) -> T:
    """Run an async unit-of-work inside a committed session scope."""

    async def _wrapped() -> T:
        async with session_scope() as db:
            return await coro_factory(db)

    return asyncio.run(_wrapped())


@celery_app.task(name="app.workers.tasks.check_expiring_subscriptions")
def check_expiring_subscriptions() -> int:
    sent = _run(alerts_service.scan_expiring)
    logger.info("check_expiring_subscriptions", sent=sent)
    return sent


@celery_app.task(name="app.workers.tasks.check_traffic_usage")
def check_traffic_usage() -> int:
    sent = _run(alerts_service.scan_usage)
    logger.info("check_traffic_usage", sent=sent)
    return sent


@celery_app.task(name="app.workers.tasks.check_low_inventory")
def check_low_inventory() -> int:
    alerts = _run(alerts_service.check_low_inventory)
    logger.info("check_low_inventory", alerts=alerts)
    return alerts


@celery_app.task(name="app.workers.tasks.expire_stale_orders")
def expire_stale_orders() -> int:
    async def _job(db):
        released = await inventory_service.release_expired_reservations(db)
        expired = await order_service.expire_stale_orders(db)
        return released + expired

    count = _run(_job)
    logger.info("expire_stale_orders", count=count)
    return count


@celery_app.task(name="app.workers.tasks.sync_panel_users")
def sync_panel_users() -> int:
    """Reconcile usage/expiry from panels. Implemented in the panel increment."""
    try:
        from app.integrations.panels.registry import sync_all
    except ImportError:
        logger.info("sync_panel_users.skipped", reason="no panel registry")
        return 0
    synced = _run(sync_all)
    logger.info("sync_panel_users", synced=synced)
    return synced


@celery_app.task(name="app.workers.tasks.poll_pending_gateway_payments")
def poll_pending_gateway_payments() -> int:
    """Reconcile unconfirmed gateway payments. Implemented in the payment increment."""
    try:
        from app.integrations.payments.poller import poll_pending
    except ImportError:
        logger.info("poll_pending_gateway_payments.skipped", reason="no gateway poller")
        return 0
    count = _run(poll_pending)
    logger.info("poll_pending_gateway_payments", count=count)
    return count


@celery_app.task(name="app.workers.tasks.send_broadcast", bind=True)
def send_broadcast(self, broadcast_id: int) -> int:
    """Fan out a broadcast to its target audience. Wired with the admin bot."""
    from app.services import broadcast_service

    async def _job(db):
        return await broadcast_service.dispatch(db, broadcast_id)

    sent = _run(_job)
    logger.info("send_broadcast", broadcast_id=broadcast_id, sent=sent)
    return sent
