"""Panel-integration interface.

Defines the data contract and dispatch used by the fulfilment service. Concrete
adapters (Marzban, X-UI) are registered in the panel-integration increment via
``get_adapter``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ProvisionResult:
    username: str
    subscription_url: str


@dataclass(slots=True)
class UsageInfo:
    used_bytes: int
    data_limit_bytes: int
    expires_at: datetime | None
    is_active: bool


async def provision_subscription(
    db: AsyncSession,
    *,
    panel_id: int,
    user_id: int,
    data_limit_bytes: int,
    expires_at: datetime,
    renew_subscription_id: int | None = None,
) -> ProvisionResult:
    """Create or renew a panel user and return its subscription URL.

    Implemented by the panel-integration increment; the adapter registry is
    consulted via :func:`app.integrations.panels.registry.get_adapter`.
    """
    from app.integrations.panels.registry import provision

    return await provision(
        db,
        panel_id=panel_id,
        user_id=user_id,
        data_limit_bytes=data_limit_bytes,
        expires_at=expires_at,
        renew_subscription_id=renew_subscription_id,
    )
