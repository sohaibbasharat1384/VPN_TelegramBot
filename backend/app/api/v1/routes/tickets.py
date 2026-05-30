"""Ticket management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import DbSession, require_permission
from app.core.permissions import Perm
from app.models.enums import SenderType, TicketStatus
from app.models.rbac import AdminUser
from app.schemas.base import Page
from app.schemas.models import (
    TicketDetail,
    TicketRead,
    TicketReplyRequest,
    TicketStatusRequest,
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=Page[TicketRead],
            dependencies=[Depends(require_permission(Perm.TICKETS_VIEW))])
async def list_tickets(
    db: DbSession,
    status: TicketStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[TicketRead]:
    tickets, total = await ticket_service.list_tickets(
        db, status=status, limit=page_size, offset=(page - 1) * page_size
    )
    return Page[TicketRead](
        items=[TicketRead.model_validate(t) for t in tickets],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{ticket_id}", response_model=TicketDetail,
            dependencies=[Depends(require_permission(Perm.TICKETS_VIEW))])
async def get_ticket(ticket_id: int, db: DbSession) -> TicketDetail:
    ticket = await ticket_service.get_or_404(db, ticket_id, with_messages=True)
    return TicketDetail.model_validate(ticket)


@router.post("/{ticket_id}/reply", response_model=TicketDetail)
async def reply_ticket(
    ticket_id: int, payload: TicketReplyRequest, db: DbSession,
    admin: AdminUser = Depends(require_permission(Perm.TICKETS_REPLY)),
) -> TicketDetail:
    await ticket_service.reply(
        db, ticket_id=ticket_id, body=payload.body,
        sender_type=SenderType.admin, sender_admin_id=admin.id,
    )
    await db.commit()
    ticket = await ticket_service.get_or_404(db, ticket_id, with_messages=True)
    return TicketDetail.model_validate(ticket)


@router.post("/{ticket_id}/status", response_model=TicketRead)
async def set_ticket_status(
    ticket_id: int, payload: TicketStatusRequest, db: DbSession,
    admin: AdminUser = Depends(require_permission(Perm.TICKETS_REPLY)),
) -> TicketRead:
    ticket = await ticket_service.set_status(db, ticket_id, payload.status)
    await db.commit()
    return TicketRead.model_validate(ticket)
