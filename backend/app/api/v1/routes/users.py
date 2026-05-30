"""User management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.schemas.base import Page
from app.schemas.models import BanRequest, UserDetail, UserRead, WalletAdjustRequest
from app.services import audit, user_service, wallet

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserRead],
            dependencies=[Depends(require_permission(Perm.USERS_VIEW))])
async def list_users(
    db: DbSession,
    q: str | None = None,
    banned: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[UserRead]:
    users, total = await user_service.search(
        db, query=q, banned=banned, limit=page_size, offset=(page - 1) * page_size
    )
    return Page[UserRead](
        items=[UserRead.model_validate(u) for u in users],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserDetail,
            dependencies=[Depends(require_permission(Perm.USERS_VIEW))])
async def get_user(user_id: int, db: DbSession) -> UserDetail:
    user = await user_service.get_or_404(db, user_id)
    balance = await wallet.get_balance(db, user_id)
    detail = UserDetail.model_validate(user)
    detail.balance = balance
    return detail


@router.post("/{user_id}/ban", response_model=UserRead)
async def ban_user(
    user_id: int, payload: BanRequest, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.USERS_BAN)),
) -> UserRead:
    user = await user_service.set_banned(db, user_id, payload.banned, reason=payload.reason)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id,
        action="user.ban" if payload.banned else "user.unban",
        target_type="user", target_id=user_id, ip_address=ip,
        new_value={"banned": payload.banned, "reason": payload.reason},
    )
    await db.commit()
    return UserRead.model_validate(user)


@router.post("/{user_id}/wallet/adjust", response_model=UserDetail)
async def adjust_wallet(
    user_id: int, payload: WalletAdjustRequest, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.WALLET_ADJUST)),
) -> UserDetail:
    await user_service.get_or_404(db, user_id)
    txn = await wallet.adjust(db, user_id, payload.delta, description=payload.description)
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="wallet.adjust",
        target_type="user", target_id=user_id, ip_address=ip,
        new_value={"delta": payload.delta, "balance_after": txn.balance_after},
    )
    await db.commit()
    user = await user_service.get_or_404(db, user_id)
    detail = UserDetail.model_validate(user)
    detail.balance = txn.balance_after
    return detail
