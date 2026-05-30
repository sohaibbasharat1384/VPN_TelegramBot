"""Abstract panel adapter contract.

Concrete adapters (Marzban, X-UI) translate these operations into the panel's
HTTP API. The registry builds the right adapter for a `panels` row.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PanelConfig:
    panel_id: int
    base_url: str
    username: str
    password: str
    extra: dict


@dataclass(slots=True)
class RemoteUser:
    username: str
    subscription_url: str
    used_bytes: int
    data_limit_bytes: int
    expires_at: datetime | None
    is_active: bool


class PanelAdapter(abc.ABC):
    """One adapter instance wraps one panel endpoint (handles its own auth)."""

    def __init__(self, config: PanelConfig):
        self.config = config

    @property
    def base_url(self) -> str:
        return self.config.base_url.rstrip("/")

    @abc.abstractmethod
    async def create_user(
        self, *, username: str, data_limit_bytes: int, expires_at: datetime
    ) -> RemoteUser:
        """Create a panel user and return its subscription URL."""

    @abc.abstractmethod
    async def renew_user(
        self, *, username: str, data_limit_bytes: int, expires_at: datetime
    ) -> RemoteUser:
        """Reset/extend an existing panel user's quota and expiry."""

    @abc.abstractmethod
    async def disable_user(self, *, username: str) -> None:
        """Disable a panel user (e.g. on refund/ban)."""

    @abc.abstractmethod
    async def get_user(self, *, username: str) -> RemoteUser | None:
        """Fetch current usage/expiry/status, or None if the user is gone."""
