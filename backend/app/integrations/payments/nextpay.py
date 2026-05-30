"""NextPay gateway. Amounts are sent in Rial (Toman × 10)."""
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

logger = get_logger("gateway.nextpay")
_BASE = "https://nextpay.org/nx/gateway"


class NextPayGateway(PaymentGateway):
    name = "nextpay"

    def __init__(self) -> None:
        self.api_key = settings.nextpay_api_key

    async def request(self, *, amount_toman, callback_url, description, order_id,
                      mobile=None, email=None) -> RequestResult:
        payload = {
            "api_key": self.api_key,
            "amount": amount_toman * TOMAN_TO_RIAL,
            "order_id": order_id,
            "callback_uri": callback_url,
            "customer_phone": mobile or "",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_BASE}/token", data=payload)
        body = resp.json()
        # code == -1 → token issued successfully.
        if body.get("code") == -1 and body.get("trans_id"):
            trans_id = body["trans_id"]
            return RequestResult(authority=trans_id, redirect_url=f"{_BASE}/payment/{trans_id}")
        logger.warning("nextpay_request_failed", body=body)
        raise PaymentError(f"nextpay request failed: code={body.get('code')}")

    async def verify(self, *, authority, amount_toman, order_id=None) -> VerifyResult:
        payload = {
            "api_key": self.api_key,
            "trans_id": authority,
            "amount": amount_toman * TOMAN_TO_RIAL,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{_BASE}/verify", data=payload)
        body = resp.json()
        # code == 0 → verified successfully.
        if body.get("code") == 0:
            return VerifyResult(success=True, ref_id=str(authority), amount_toman=amount_toman)
        return VerifyResult(success=False, message=f"code={body.get('code')}")
