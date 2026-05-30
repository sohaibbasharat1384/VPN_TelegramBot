"""Marzban panel adapter (https://github.com/Gozargah/Marzban).

Authenticates with the admin token endpoint and manages users via /api/user.
Inbound/proxy templates are taken from ``panel.extra`` so deployments can pin
their own protocols, e.g.::

    {
      "proxies": {"vless": {"flow": ""}},
      "inbounds": {"vless": ["VLESS TCP REALITY"]}
    }
"""
from __future__ import annotations

from datetime import UTC, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import PanelIntegrationError
from app.core.logging import get_logger
from app.integrations.panels.base import PanelAdapter, RemoteUser

logger = get_logger("panel.marzban")

_DEFAULT_PROXIES = {"vless": {"flow": ""}}
_DEFAULT_INBOUNDS: dict[str, list[str]] = {}


class MarzbanAdapter(PanelAdapter):
    def __init__(self, config):
        super().__init__(config)
        self._token: str | None = None

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=20)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, max=4), reraise=True)
    async def _auth(self) -> str:
        if self._token:
            return self._token
        async with await self._client() as client:
            resp = await client.post(
                "/api/admin/token",
                data={"username": self.config.username, "password": self.config.password},
            )
        if resp.status_code != 200:
            raise PanelIntegrationError(f"marzban auth failed: {resp.status_code}")
        self._token = resp.json()["access_token"]
        return self._token

    async def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self._auth()}"}

    def _to_remote(self, data: dict) -> RemoteUser:
        sub = data.get("subscription_url", "")
        if sub.startswith("/"):
            sub = f"{self.base_url}{sub}"
        expire = data.get("expire")
        return RemoteUser(
            username=data["username"],
            subscription_url=sub,
            used_bytes=int(data.get("used_traffic", 0) or 0),
            data_limit_bytes=int(data.get("data_limit", 0) or 0),
            expires_at=datetime.fromtimestamp(expire, tz=UTC) if expire else None,
            is_active=data.get("status") == "active",
        )

    async def create_user(self, *, username, data_limit_bytes, expires_at) -> RemoteUser:
        payload = {
            "username": username,
            "status": "active",
            "data_limit": data_limit_bytes,
            "expire": int(expires_at.timestamp()),
            "proxies": self.config.extra.get("proxies", _DEFAULT_PROXIES),
            "inbounds": self.config.extra.get("inbounds", _DEFAULT_INBOUNDS),
            "data_limit_reset_strategy": "no_reset",
        }
        async with await self._client() as client:
            resp = await client.post("/api/user", json=payload, headers=await self._headers())
        if resp.status_code not in (200, 201):
            logger.warning("marzban_create_failed", status=resp.status_code, body=resp.text[:200])
            raise PanelIntegrationError(f"marzban create failed: {resp.status_code}")
        return self._to_remote(resp.json())

    async def renew_user(self, *, username, data_limit_bytes, expires_at) -> RemoteUser:
        payload = {
            "status": "active",
            "data_limit": data_limit_bytes,
            "expire": int(expires_at.timestamp()),
        }
        async with await self._client() as client:
            resp = await client.put(
                f"/api/user/{username}", json=payload, headers=await self._headers()
            )
            if resp.status_code == 404:
                return await self.create_user(
                    username=username, data_limit_bytes=data_limit_bytes, expires_at=expires_at
                )
            # Reset used traffic so the renewed quota starts fresh.
            await client.post(f"/api/user/{username}/reset", headers=await self._headers())
        if resp.status_code != 200:
            raise PanelIntegrationError(f"marzban renew failed: {resp.status_code}")
        return self._to_remote(resp.json())

    async def disable_user(self, *, username) -> None:
        async with await self._client() as client:
            await client.put(
                f"/api/user/{username}", json={"status": "disabled"}, headers=await self._headers()
            )

    async def get_user(self, *, username) -> RemoteUser | None:
        async with await self._client() as client:
            resp = await client.get(f"/api/user/{username}", headers=await self._headers())
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise PanelIntegrationError(f"marzban get failed: {resp.status_code}")
        return self._to_remote(resp.json())
