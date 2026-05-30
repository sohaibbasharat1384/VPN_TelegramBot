"""Reconcile gateway payments that lack a callback (user closed the tab, etc.)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaymentError
from app.core.logging import get_logger
from app.models.enums import PaymentMethod, PaymentStatus
from app.models.order import Payment
from app.services import payment_service

logger = get_logger("gateway.poller")

# Verify payments at least this old (give the user time) but not stale beyond TTL.
_MIN_AGE = timedelta(minutes=2)
_MAX_AGE = timedelta(hours=24)


async def poll_pending(db: AsyncSession) -> int:
    now = datetime.now(UTC)
    rows = await db.execute(
        select(Payment).where(
            Payment.method == PaymentMethod.gateway,
            Payment.status == PaymentStatus.pending,
            Payment.gateway_authority.isnot(None),
            Payment.created_at <= now - _MIN_AGE,
            Payment.created_at >= now - _MAX_AGE,
        )
    )
    settled = 0
    for payment in rows.scalars().all():
        try:
            _, ok = await payment_service.verify_and_settle(db, payment.gateway_authority)
            settled += int(bool(ok))
        except PaymentError as exc:
            logger.warning("poll_verify_error", payment_id=payment.id, error=str(exc))
    return settled
