"""IDPay gateway (v1.1). Amounts are sent in Rial (Toman × 10)."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.exceptions import PaymentError
from app.core.logging import get_logger
from app.integrations.payments.base import (
    TOMAN_TO_RIAL,
    PaymentGateway,
    RequestResult,
    VerifyResult,
)

logger = get_logger("gateway.idpay")
_API = "https://api.idpay.ir/v1.1"


class IDPayGateway(PaymentGateway):
    name = "idpay"

    def __init__(self) -> None:
        self.api_key = settings.idpay_api_key
        self.sandbox = settings.idpay_sandbox

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": self.api_key,
            "X-SANDBOX": "1" if self.sandbox else "0",
            "Content-Type": "application/json",
        }

    async def request(self, *, amount_toman, callback_url, description, order_id,
                      mobile=None, email=None) -> RequestResult:
        payload = {
            "order_id": order_id,
            "amount": amount_toman * TOMAN_TO_RIAL,
            "callback": callback_url,
            "desc": description,
            "phone": mobile or "",
            "mail": email or "",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_API}/payment", json=payload, headers=self._headers())
        body = resp.json()
        if resp.status_code == 201 and body.get("id") and body.get("link"):
            return RequestResult(authority=body["id"], redirect_url=body["link"])
        logger.warning("idpay_request_failed", body=body)
        raise PaymentError(str(body.get("error_message") or "idpay request failed"))

    async def verify(self, *, authority, amount_toman, order_id=None) -> VerifyResult:
        payload = {"id": authority, "order_id": order_id or authority}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_API}/payment/verify", json=payload, headers=self._headers())
        body = resp.json()
        # status 100 = verified & successful.
        if body.get("status") == 100:
            paid_rial = int(body.get("amount", 0))
            return VerifyResult(
                success=True,
                ref_id=str(body.get("track_id")),
                amount_toman=paid_rial // TOMAN_TO_RIAL,
            )
        return VerifyResult(success=False, message=str(body.get("error_message") or body.get("status")))
