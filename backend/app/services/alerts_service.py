"""Automated alert scans run by Celery beat: expiry, usage, low inventory."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.catalog import Plan
from app.models.enums import NotificationKind, SubscriptionStatus
from app.models.order import Subscription
from app.models.user import User
from app.services import (
    admin_service,
    inventory_service,
    notification_service,
    settings_service,
)
from app.utils.formatting import gb, human_bytes, jalali
from app.utils.telegram import send_message

# day-threshold → (alert tag stored on the subscription, notification kind)
_EXPIRY_STEPS = [
    (7, "7", NotificationKind.expiry_7),
    (3, "3", NotificationKind.expiry_3),
    (1, "1", NotificationKind.expiry_1),
]


async def scan_expiring(db: AsyncSession) -> int:
    """Send 7/3/1-day and expired alerts; flip expired subscriptions."""
    now = datetime.now(UTC)
    sent = 0
    rows = await db.execute(
        select(Subscription, User)
        .join(User, User.id == Subscription.user_id)
        .where(Subscription.status == SubscriptionStatus.active)
    )
    for sub, user in rows.all():
        seconds_left = (sub.expires_at - now).total_seconds()
        days_left = seconds_left / 86400
        already = set(sub.expiry_alerts_sent or [])

        if seconds_left <= 0:
            sub.status = SubscriptionStatus.expired
            if "expired" not in already:
                text = (
                    f"⛔️ اشتراک شما منقضی شد.\n"
                    f"حجم: {gb(sub.data_limit_bytes // 1024**3)}\n"
                    f"برای تمدید، از منوی «تمدید اشتراک» استفاده کنید."
                )
                if await notification_service.notify(
                    db, user, NotificationKind.expired, text, reference_id=sub.id
                ):
                    sent += 1
                sub.expiry_alerts_sent = [*already, "expired"]
            continue

        for threshold_days, tag, kind in _EXPIRY_STEPS:
            if days_left <= threshold_days and tag not in already:
                text = (
                    f"⏳ <b>{threshold_days} روز</b> تا پایان اشتراک شما باقی مانده است.\n"
                    f"تاریخ انقضا: {jalali(sub.expires_at)}\n"
                    f"برای تمدید، «تمدید اشتراک» را بزنید."
                )
                if await notification_service.notify(db, user, kind, text, reference_id=sub.id):
                    sent += 1
                already.add(tag)
                sub.expiry_alerts_sent = sorted(already, reverse=True)
                break
    await db.flush()
    return sent


async def scan_usage(db: AsyncSession) -> int:
    """Send 80/90/100% data-usage alerts (relevant to panel-synced subs)."""
    sent = 0
    rows = await db.execute(
        select(Subscription, User)
        .join(User, User.id == Subscription.user_id)
        .where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.data_limit_bytes > 0,
        )
    )
    for sub, user in rows.all():
        pct = sub.data_used_bytes * 100 // sub.data_limit_bytes
        target_level, kind = None, None
        if pct >= 100:
            target_level, kind = 100, NotificationKind.usage_100
        elif pct >= 90:
            target_level, kind = 90, NotificationKind.usage_90
        elif pct >= 80:
            target_level, kind = 80, NotificationKind.usage_80

        if target_level is None or sub.usage_alert_level >= target_level:
            continue
        text = (
            f"📊 شما <b>{pct}٪</b> از حجم اشتراک خود را مصرف کرده‌اید.\n"
            f"مصرف: {human_bytes(sub.data_used_bytes)} از {human_bytes(sub.data_limit_bytes)}"
        )
        if await notification_service.notify(db, user, kind, text, reference_id=sub.id):
            sent += 1
        sub.usage_alert_level = target_level
    await db.flush()
    return sent


async def check_low_inventory(db: AsyncSession) -> int:
    """Alert admins (once per day per plan) when a manual plan runs low."""
    threshold = await settings_service.get_int(
        db, "low_inventory_threshold", settings.low_inventory_threshold
    )
    today = date.today().isoformat()
    alerts = 0
    plans = (await db.execute(select(Plan).where(Plan.is_active.is_(True)))).scalars().all()
    chat_ids = await admin_service.admin_chat_ids(db)
    for plan in plans:
        available = await inventory_service.available_count(db, plan.id)
        if available > threshold:
            continue
        key = f"low_inv_alert_{plan.id}"
        if await settings_service.get(db, key) == today:
            continue
        text = (
            f"⚠️ <b>هشدار موجودی</b>\n"
            f"پلن «{plan.title}» تنها <b>{available}</b> کانفیگ آماده دارد "
            f"(آستانه: {threshold}).\nلطفاً انبار را شارژ کنید."
        )
        for chat_id in chat_ids:
            if await send_message(settings.admin_bot_token, chat_id, text):
                alerts += 1
        await settings_service.set_value(db, key, today)
    await db.flush()
    return alerts
