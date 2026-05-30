"""Gateway factory — selects the active provider from settings (replaceable)."""
from __future__ import annotations

from app.core.config import settings
from app.integrations.payments.base import PaymentGateway
from app.integrations.payments.idpay import IDPayGateway
from app.integrations.payments.nextpay import NextPayGateway
from app.integrations.payments.zarinpal import ZarinPalGateway

_REGISTRY: dict[str, type[PaymentGateway]] = {
    "zarinpal": ZarinPalGateway,
    "idpay": IDPayGateway,
    "nextpay": NextPayGateway,
}


def get_gateway(provider: str | None = None) -> PaymentGateway:
    name = (provider or settings.payment_provider).lower()
    gateway_cls = _REGISTRY.get(name)
    if gateway_cls is None:
        raise ValueError(f"unknown payment provider: {name}")
    return gateway_cls()
