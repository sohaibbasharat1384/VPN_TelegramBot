"""Customer bot router aggregation."""
from __future__ import annotations

from aiogram import Router

from app.bot.customer.handlers import (
    fallback,
    menu,
    purchase,
    referral,
    subscriptions,
    tickets,
    wallet,
)


def build_router() -> Router:
    router = Router(name="customer")
    router.include_router(menu.router)
    router.include_router(purchase.router)
    router.include_router(subscriptions.router)
    router.include_router(wallet.router)
    router.include_router(referral.router)
    router.include_router(tickets.router)
    router.include_router(fallback.router)  # must be last (catch-all)
    return router
