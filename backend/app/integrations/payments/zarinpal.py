"""ZarinPal gateway (Payment API v4). Uses currency IRT so amounts stay in Toman."""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.payments.base import PaymentGateway, RequestResult, VerifyResult

logger = get_logger("gateway.zarinpal")


class ZarinPalGateway(PaymentGateway):
    name = "zarinpal"

    def __init__(self) -> None:
        self.merchant_id = settings.zarinpal_merchant_id
        host = "sandbox.zarinpal.com" if settings.zarinpal_sandbox else "payment.zarinpal.com"
        self._api = f"https://{host}/pg/v4/payment"
        self._startpay = f"https://{host}/pg/StartPay"

    async def request(self, *, amount_toman, callback_url, description, order_id,
                      mobile=None, email=None) -> RequestResult:
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_toman,
            "currency": "IRT",
            "callback_url": callback_url,
            "description": description,
            "metadata": {"order_id": order_id, "mobile": mobile or "", "email": email or ""},
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{self._api}/request.json", json=payload)
        body = resp.json()
        data = body.get("data") or {}
        if data.get("code") in (100, 101) and data.get("authority"):
            authority = data["authority"]
            return RequestResult(authority=authority, redirect_url=f"{self._startpay}/{authority}")
        logger.warning("zarinpal_request_failed", errors=body.get("errors"))
        raise _gateway_error(body)

    async def verify(self, *, authority, amount_toman, order_id=None) -> VerifyResult:
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount_toman,
            "currency": "IRT",
            "authority": authority,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{self._api}/verify.json", json=payload)
        body = resp.json()
        data = body.get("data") or {}
        # 100 = paid now, 101 = already verified.
        if data.get("code") in (100, 101):
            return VerifyResult(
                success=True, ref_id=str(data.get("ref_id")), amount_toman=amount_toman
            )
        return VerifyResult(success=False, message=str(body.get("errors") or "verify failed"))


def _gateway_error(body: dict):
    from app.core.exceptions import PaymentError

    return PaymentError(str(body.get("errors") or "zarinpal request failed"))
