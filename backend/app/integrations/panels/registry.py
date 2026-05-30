"""Panel adapter registry, provisioning, and usage sync."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PanelIntegrationError
from app.core.security import decrypt_secret
from app.integrations.panels import ProvisionResult
from app.integrations.panels.base import PanelAdapter, PanelConfig
from app.integrations.panels.marzban import MarzbanAdapter
from app.integrations.panels.xui import XUIAdapter
from app.models.catalog import Panel
from app.models.enums import PanelType, SubscriptionStatus
from app.models.order import Subscription
from app.utils.codes import random_code

_ADAPTERS: dict[PanelType, type[PanelAdapter]] = {
    PanelType.marzban: MarzbanAdapter,
    PanelType.xui: XUIAdapter,
}


async def get_adapter(db: AsyncSession, panel_id: int) -> PanelAdapter:
    panel = await db.get(Panel, panel_id)
    if panel is None or not panel.is_active:
        raise PanelIntegrationError("panel not found or inactive")
    adapter_cls = _ADAPTERS.get(panel.type)
    if adapter_cls is None:
        raise PanelIntegrationError(f"unsupported panel type {panel.type}")
    config = PanelConfig(
        panel_id=panel.id,
        base_url=panel.base_url,
        username=panel.username,
        password=decrypt_secret(panel.password_enc),
        extra=panel.extra or {},
    )
    return adapter_cls(config)


def _make_username(user_id: int) -> str:
    return f"u{user_id}_{random_code(5).lower()}"


async def provision(
    db: AsyncSession,
    *,
    panel_id: int,
    user_id: int,
    data_limit_bytes: int,
    expires_at: datetime,
    renew_subscription_id: int | None = None,
) -> ProvisionResult:
    adapter = await get_adapter(db, panel_id)

    if renew_subscription_id:
        old = await db.get(Subscription, renew_subscription_id)
        if old is not None and old.panel_username:
            remote = await adapter.renew_user(
                username=old.panel_username,
                data_limit_bytes=data_limit_bytes,
                expires_at=expires_at,
            )
            return ProvisionResult(username=remote.username, subscription_url=remote.subscription_url)

    username = _make_username(user_id)
    remote = await adapter.create_user(
        username=username, data_limit_bytes=data_limit_bytes, expires_at=expires_at
    )
    return ProvisionResult(username=remote.username, subscription_url=remote.subscription_url)


async def sync_all(db: AsyncSession) -> int:
    """Reconcile usage/expiry/status for all active panel-backed subscriptions."""
    rows = await db.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.panel_id.isnot(None),
            Subscription.panel_username.isnot(None),
        )
    )
    subs = list(rows.scalars().all())
    adapters: dict[int, PanelAdapter] = {}
    synced = 0
    for sub in subs:
        try:
            adapter = adapters.get(sub.panel_id)
            if adapter is None:
                adapter = await get_adapter(db, sub.panel_id)
                adapters[sub.panel_id] = adapter
            remote = await adapter.get_user(username=sub.panel_username)
        except PanelIntegrationError:
            continue
        if remote is None:
            continue
        sub.data_used_bytes = remote.used_bytes
        if remote.data_limit_bytes:
            sub.data_limit_bytes = remote.data_limit_bytes
        if remote.expires_at is not None:
            sub.expires_at = remote.expires_at
        if not remote.is_active:
            sub.status = SubscriptionStatus.disabled
        synced += 1
    await db.flush()
    return synced
