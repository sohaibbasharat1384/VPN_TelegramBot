"""Plan & pricing management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.schemas.models import PlanCreate, PlanRead, PlanUpdate
from app.services import audit, plan_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanRead],
            dependencies=[Depends(require_permission(Perm.DASHBOARD_VIEW))])
async def list_plans(db: DbSession) -> list[PlanRead]:
    return [PlanRead.model_validate(p) for p in await plan_service.list_all(db)]


@router.post("", response_model=PlanRead)
async def create_plan(
    payload: PlanCreate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.PLANS_MANAGE)),
) -> PlanRead:
    plan = await plan_service.create(db, **payload.model_dump())
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="plan.create",
        target_type="plan", target_id=plan.id, ip_address=ip, new_value=payload.model_dump(mode="json"),
    )
    await db.commit()
    return PlanRead.model_validate(plan)


@router.patch("/{plan_id}", response_model=PlanRead)
async def update_plan(
    plan_id: int, payload: PlanUpdate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.PLANS_MANAGE)),
) -> PlanRead:
    before = await plan_service.get_or_404(db, plan_id)
    old = {"price": before.price, "is_active": before.is_active, "title": before.title}
    plan = await plan_service.update(db, plan_id, **payload.model_dump(exclude_none=True))
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="plan.update",
        target_type="plan", target_id=plan_id, ip_address=ip,
        old_value=old, new_value=payload.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()
    return PlanRead.model_validate(plan)
