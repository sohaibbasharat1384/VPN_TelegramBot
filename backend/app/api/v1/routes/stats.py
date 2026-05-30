"""Dashboard statistics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import DbSession, require_permission
from app.core.permissions import Perm
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", dependencies=[Depends(require_permission(Perm.STATS_VIEW))])
async def overview(db: DbSession) -> dict:
    return await stats_service.overview(db)


@router.get("/revenue-series", dependencies=[Depends(require_permission(Perm.STATS_VIEW))])
async def revenue_series(db: DbSession, days: int = 14) -> list[dict]:
    return await stats_service.revenue_series(db, days=min(max(days, 1), 90))
