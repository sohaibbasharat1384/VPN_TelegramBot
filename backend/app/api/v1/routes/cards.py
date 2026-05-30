"""Card-to-card destination management."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import ClientIP, DbSession, require_permission
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.order import PaymentCard
from app.models.rbac import AdminUser
from app.schemas.models import CardCreate, CardRead
from app.services import audit

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("", response_model=list[CardRead],
            dependencies=[Depends(require_permission(Perm.CARDS_MANAGE))])
async def list_cards(db: DbSession) -> list[CardRead]:
    from sqlalchemy import select

    rows = (await db.execute(select(PaymentCard).order_by(PaymentCard.sort_order))).scalars().all()
    return [CardRead.model_validate(c) for c in rows]


@router.post("", response_model=CardRead)
async def create_card(
    payload: CardCreate, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.CARDS_MANAGE)),
) -> CardRead:
    card = PaymentCard(**payload.model_dump())
    db.add(card)
    await db.flush()
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="card.create",
        target_type="card", target_id=card.id, ip_address=ip,
        new_value={"bank_name": card.bank_name},
    )
    await db.commit()
    return CardRead.model_validate(card)


@router.post("/{card_id}/toggle", response_model=CardRead)
async def toggle_card(
    card_id: int, db: DbSession, ip: ClientIP,
    admin: AdminUser = Depends(require_permission(Perm.CARDS_MANAGE)),
) -> CardRead:
    card = await db.get(PaymentCard, card_id)
    if card is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(user_message="کارت یافت نشد.")
    card.is_active = not card.is_active
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="card.toggle",
        target_type="card", target_id=card_id, ip_address=ip,
        new_value={"is_active": card.is_active},
    )
    await db.commit()
    return CardRead.model_validate(card)
