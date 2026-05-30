"""Aggregate API router. Sub-routers are mounted here as increments land."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    cards,
    coupons,
    inventory,
    payments,
    plans,
    settings,
    stats,
    tickets,
    users,
)

api_router = APIRouter()
for module in (auth, stats, users, plans, inventory, payments, coupons, tickets, cards, settings):
    api_router.include_router(module.router)
