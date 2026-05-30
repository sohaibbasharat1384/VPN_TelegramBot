"""Coupon management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.permissions import Perm
from app.models.coupon import Coupon
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.schemas.models import CouponCreate, CouponRead
from app.services import audit, coupon_service

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("", response_model=list[CouponRead],
            dependencies=[Depends(require_permission(Perm.COUPONS_MANAGE))])
async def list_coupons(db: DbSession) -> list[CouponRead]:
    rows = (await db.execute(select(Coupon).order_by(Coupon.created_at.desc()))).scalars().all()
    return [CouponRead.model_validate(c) for c in rows]


@router.post("", response_model=CouponRead)
async def create_coupon(
    payload: CouponCreate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.COUPONS_MANAGE)),
) -> CouponRead:
    coupon = await coupon_service.create(db, **payload.model_dump())
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="coupon.create",
        target_type="coupon", target_id=coupon.id, ip_address=ip,
        new_value={"code": coupon.code},
    )
    await db.commit()
    return CouponRead.model_validate(coupon)


@router.post("/{coupon_id}/toggle", response_model=CouponRead)
async def toggle_coupon(
    coupon_id: int, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.COUPONS_MANAGE)),
) -> CouponRead:
    coupon = await coupon_service.get_or_404(db, coupon_id)
    coupon = await coupon_service.set_active(db, coupon_id, not coupon.is_active)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="coupon.toggle",
        target_type="coupon", target_id=coupon_id, ip_address=ip,
        new_value={"is_active": coupon.is_active},
    )
    await db.commit()
    return CouponRead.model_validate(coupon)
