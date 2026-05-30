"""Payment review endpoints (approve / reject / list)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.permissions import Perm
from app.models.enums import ActorType, PaymentStatus
from app.models.rbac import AdminUser
from app.schemas.base import Page
from app.schemas.models import PaymentRead, PaymentReviewRequest
from app.services import audit, payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=Page[PaymentRead],
            dependencies=[Depends(require_permission(Perm.PAYMENTS_VIEW))])
async def list_payments(
    db: DbSession,
    status: PaymentStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[PaymentRead]:
    payments, total = await payment_service.list_payments(
        db, status=status, limit=page_size, offset=(page - 1) * page_size
    )
    return Page[PaymentRead](
        items=[PaymentRead.model_validate(p) for p in payments],
        total=total, page=page, page_size=page_size,
    )


@router.post("/{payment_id}/approve", response_model=PaymentRead)
async def approve_payment(
    payment_id: int, payload: PaymentReviewRequest, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.PAYMENTS_APPROVE)),
) -> PaymentRead:
    payment = await payment_service.get_or_404(db, payment_id)
    await payment_service.approve(db, payment, admin_id=admin.id, note=payload.note)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="payment.approve",
        target_type="payment", target_id=payment_id, ip_address=ip,
        new_value={"amount": payment.amount, "note": payload.note},
    )
    await db.commit()
    return PaymentRead.model_validate(payment)


@router.post("/{payment_id}/reject", response_model=PaymentRead)
async def reject_payment(
    payment_id: int, payload: PaymentReviewRequest, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.PAYMENTS_APPROVE)),
) -> PaymentRead:
    payment = await payment_service.get_or_404(db, payment_id)
    await payment_service.reject(db, payment, admin_id=admin.id, note=payload.note)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="payment.reject",
        target_type="payment", target_id=payment_id, ip_address=ip,
        new_value={"note": payload.note},
    )
    await db.commit()
    return PaymentRead.model_validate(payment)
