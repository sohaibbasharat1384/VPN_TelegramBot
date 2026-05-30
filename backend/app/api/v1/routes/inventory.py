"""Inventory (ready-to-sell configs) endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.config import settings
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.schemas.models import ConfigCreate, InventoryCount
from app.services import audit, inventory_service, plan_service, settings_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/counts", response_model=list[InventoryCount],
            dependencies=[Depends(require_permission(Perm.INVENTORY_VIEW))])
async def inventory_counts(db: DbSession) -> list[InventoryCount]:
    counts = await inventory_service.counts_by_plan(db)
    threshold = await settings_service.get_int(
        db, "low_inventory_threshold", settings.low_inventory_threshold
    )
    plans = await plan_service.list_all(db)
    result: list[InventoryCount] = []
    for plan in plans:
        c = counts.get(plan.id, {})
        available = c.get("available", 0)
        result.append(
            InventoryCount(
                plan_id=plan.id, title=plan.title,
                available=available, reserved=c.get("reserved", 0), sold=c.get("sold", 0),
                low=available <= threshold,
            )
        )
    return result


@router.post("/configs", status_code=201)
async def add_config(
    payload: ConfigCreate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.INVENTORY_MANAGE)),
) -> dict:
    config = await inventory_service.add_config(
        db,
        plan_id=payload.plan_id,
        subscription_url=payload.subscription_url,
        raw_config=payload.raw_config,
        remark=payload.remark,
    )
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="inventory.add",
        target_type="config", target_id=config.id, ip_address=ip,
        new_value={"plan_id": payload.plan_id},
    )
    await db.commit()
    return {"id": config.id, "status": config.status.value}
