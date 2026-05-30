"""Sanaei X-UI / 3x-ui panel adapter.

Authenticates via the session-cookie login and manages clients on a configured
inbound. Required ``panel.extra`` keys::

    {
      "inbound_id": 1,
      "sub_url_base": "https://domain:2096/sub",   # 3x-ui subscription service
      "flow": "xtls-rprx-vision"                     # optional, for VLESS reality
    }

Each subscription maps to one inbound client identified by `email` (== username)
with a stable `subId` used to build the subscription URL.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import PanelIntegrationError
from app.core.logging import get_logger
from app.integrations.panels.base import PanelAdapter, RemoteUser

logger = get_logger("panel.xui")


class XUIAdapter(PanelAdapter):
    def __init__(self, config):
        super().__init__(config)
        self._cookie: str | None = None

    @property
    def inbound_id(self) -> int:
        return int(self.config.extra.get("inbound_id", 1))

    def _sub_url(self, sub_id: str) -> str:
        base = self.config.extra.get("sub_url_base", f"{self.base_url}/sub").rstrip("/")
        return f"{base}/{sub_id}"

    async def _client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(base_url=self.base_url, timeout=20)
        if self._cookie:
            client.headers["Cookie"] = self._cookie
        return client

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, max=4), reraise=True)
    async def _auth(self) -> None:
        if self._cookie:
            return
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20) as client:
            resp = await client.post(
                "/login",
                data={"username": self.config.username, "password": self.config.password},
            )
        if resp.status_code != 200 or not resp.json().get("success"):
            raise PanelIntegrationError("xui auth failed")
        cookies = resp.cookies
        self._cookie = "; ".join(f"{k}={v}" for k, v in cookies.items())

    def _client_settings(self, *, client_uuid: str, email: str, data_limit_bytes: int,
                          expires_at: datetime, sub_id: str) -> str:
        return json.dumps(
            {
                "clients": [
                    {
                        "id": client_uuid,
                        "email": email,
                        "totalGB": data_limit_bytes,
                        "expiryTime": int(expires_at.timestamp() * 1000),
                        "enable": True,
                        "tgId": "",
                        "subId": sub_id,
                        "flow": self.config.extra.get("flow", ""),
                    }
                ]
            }
        )

    async def create_user(self, *, username, data_limit_bytes, expires_at) -> RemoteUser:
        await self._auth()
        client_uuid = str(uuid.uuid4())
        sub_id = username
        settings = self._client_settings(
            client_uuid=client_uuid, email=username, data_limit_bytes=data_limit_bytes,
            expires_at=expires_at, sub_id=sub_id,
        )
        async with await self._client() as client:
            resp = await client.post(
                "/panel/api/inbounds/addClient",
                data={"id": self.inbound_id, "settings": settings},
            )
        if resp.status_code != 200 or not resp.json().get("success"):
            logger.warning("xui_create_failed", status=resp.status_code, body=resp.text[:200])
            raise PanelIntegrationError("xui create failed")
        return RemoteUser(
            username=username,
            subscription_url=self._sub_url(sub_id),
            used_bytes=0,
            data_limit_bytes=data_limit_bytes,
            expires_at=expires_at,
            is_active=True,
        )

    async def renew_user(self, *, username, data_limit_bytes, expires_at) -> RemoteUser:
        await self._auth()
        existing = await self.get_user(username=username)
        if existing is None:
            return await self.create_user(
                username=username, data_limit_bytes=data_limit_bytes, expires_at=expires_at
            )
        client_uuid = existing.username  # placeholder; updateClient keyed by uuid below
        settings = self._client_settings(
            client_uuid=str(uuid.uuid4()), email=username, data_limit_bytes=data_limit_bytes,
            expires_at=expires_at, sub_id=username,
        )
        async with await self._client() as client:
            # Reset traffic counters, then push new quota/expiry.
            await client.post(f"/panel/api/inbounds/{self.inbound_id}/resetClientTraffic/{username}")
            resp = await client.post(
                f"/panel/api/inbounds/updateClient/{client_uuid}",
                data={"id": self.inbound_id, "settings": settings},
            )
        if resp.status_code != 200 or not resp.json().get("success"):
            raise PanelIntegrationError("xui renew failed")
        return RemoteUser(
            username=username, subscription_url=self._sub_url(username), used_bytes=0,
            data_limit_bytes=data_limit_bytes, expires_at=expires_at, is_active=True,
        )

    async def disable_user(self, *, username) -> None:
        await self._auth()
        async with await self._client() as client:
            await client.post(f"/panel/api/inbounds/{self.inbound_id}/delClient/{username}")

    async def get_user(self, *, username) -> RemoteUser | None:
        await self._auth()
        async with await self._client() as client:
            resp = await client.get(f"/panel/api/inbounds/getClientTraffics/{username}")
        if resp.status_code != 200:
            return None
        body = resp.json()
        obj = body.get("obj")
        if not obj:
            return None
        used = int(obj.get("up", 0)) + int(obj.get("down", 0))
        expiry_ms = obj.get("expiryTime") or 0
        return RemoteUser(
            username=username,
            subscription_url=self._sub_url(username),
            used_bytes=used,
            data_limit_bytes=int(obj.get("total", 0) or 0),
            expires_at=datetime.fromtimestamp(expiry_ms / 1000, tz=UTC) if expiry_ms else None,
            is_active=bool(obj.get("enable", True)),
        )
