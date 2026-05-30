"""Payment gateway abstraction.

Internal amounts are always integer **Toman**. Adapters convert to the unit each
gateway expects (e.g. Rial = Toman × 10) at the boundary.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

TOMAN_TO_RIAL = 10


@dataclass(slots=True)
class RequestResult:
    authority: str          # gateway transaction id we persist
    redirect_url: str       # where to send the user to pay


@dataclass(slots=True)
class VerifyResult:
    success: bool
    ref_id: str | None = None      # settlement reference on success
    amount_toman: int | None = None
    message: str = ""


class PaymentGateway(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def request(
        self, *, amount_toman: int, callback_url: str, description: str,
        order_id: str, mobile: str | None = None, email: str | None = None,
    ) -> RequestResult:
        ...

    @abc.abstractmethod
    async def verify(self, *, authority: str, amount_toman: int, order_id: str | None = None) -> VerifyResult:
        ...
