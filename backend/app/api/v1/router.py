"""Aggregate API router. Sub-routers are mounted here as increments land."""
from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# Routers added in later increments:
#   from app.api.v1.routes import auth, users, payments, plans, inventory, ...
#   api_router.include_router(auth.router)
