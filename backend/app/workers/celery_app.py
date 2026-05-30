"""Celery application and beat schedule."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "vpnrobot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "check-expiring-subscriptions": {
        "task": "app.workers.tasks.check_expiring_subscriptions",
        "schedule": crontab(minute=0),  # hourly
    },
    "check-traffic-usage": {
        "task": "app.workers.tasks.check_traffic_usage",
        "schedule": crontab(minute="*/15"),
    },
    "sync-panel-users": {
        "task": "app.workers.tasks.sync_panel_users",
        "schedule": crontab(minute="*/30"),
    },
    "check-low-inventory": {
        "task": "app.workers.tasks.check_low_inventory",
        "schedule": crontab(minute=5),  # hourly, offset
    },
    "poll-pending-gateway-payments": {
        "task": "app.workers.tasks.poll_pending_gateway_payments",
        "schedule": crontab(minute="*/5"),
    },
    "expire-stale-orders": {
        "task": "app.workers.tasks.expire_stale_orders",
        "schedule": crontab(minute="*/15"),
    },
}
