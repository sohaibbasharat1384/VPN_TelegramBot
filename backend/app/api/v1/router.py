"""Aggregate API router. Sub-routers are mounted here as increments land."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth

api_router = APIRouter()
api_router.include_router(auth.router)

# More routers added in later increments:
#   users, payments, plans, inventory, coupons, referrals, tickets, stats, ...
