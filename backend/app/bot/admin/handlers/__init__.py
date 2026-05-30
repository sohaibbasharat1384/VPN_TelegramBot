"""Admin bot router aggregation."""
from __future__ import annotations

from aiogram import Router

from app.bot.admin.handlers import (
    broadcast,
    cards,
    coupons,
    inventory,
    menu,
    payments,
    stats,
    tickets,
    users,
)


def build_router() -> Router:
    router = Router(name="admin")
    router.include_router(menu.router)
    router.include_router(payments.router)
    router.include_router(stats.router)
    router.include_router(users.router)
    router.include_router(tickets.router)
    router.include_router(inventory.router)
    router.include_router(coupons.router)
    router.include_router(cards.router)
    router.include_router(broadcast.router)
    return router
