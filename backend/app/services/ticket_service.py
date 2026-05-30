"""Support ticket service: create, reply, close, reopen, list."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import SenderType, TicketStatus
from app.models.ticket import Ticket, TicketMessage


async def create_ticket(
    db: AsyncSession, *, user_id: int, subject: str, body: str, attachment_path: str | None = None
) -> Ticket:
    now = datetime.now(UTC)
    ticket = Ticket(user_id=user_id, subject=subject[:160], status=TicketStatus.open, last_message_at=now)
    db.add(ticket)
    await db.flush()
    db.add(
        TicketMessage(
            ticket_id=ticket.id,
            sender_type=SenderType.user,
            sender_user_id=user_id,
            body=body,
            attachment_path=attachment_path,
        )
    )
    await db.flush()
    return ticket


async def get_or_404(db: AsyncSession, ticket_id: int, *, with_messages: bool = False) -> Ticket:
    stmt = select(Ticket).where(Ticket.id == ticket_id)
    if with_messages:
        stmt = stmt.options(selectinload(Ticket.messages))
    ticket = (await db.execute(stmt)).scalar_one_or_none()
    if ticket is None:
        raise NotFoundError(user_message="تیکت یافت نشد.")
    return ticket


async def reply(
    db: AsyncSession,
    *,
    ticket_id: int,
    body: str,
    sender_type: SenderType,
    sender_user_id: int | None = None,
    sender_admin_id: int | None = None,
    attachment_path: str | None = None,
) -> TicketMessage:
    ticket = await get_or_404(db, ticket_id)
    if ticket.status == TicketStatus.closed:
        raise ValidationError(user_message="این تیکت بسته شده است.")
    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type=sender_type,
        sender_user_id=sender_user_id,
        sender_admin_id=sender_admin_id,
        body=body,
        attachment_path=attachment_path,
    )
    db.add(msg)
    ticket.last_message_at = datetime.now(UTC)
    # User reply → pending (needs staff); staff reply → answered.
    ticket.status = TicketStatus.pending if sender_type == SenderType.user else TicketStatus.answered
    if sender_type == SenderType.admin and sender_admin_id:
        ticket.assigned_admin_id = sender_admin_id
    await db.flush()
    return msg


async def set_status(db: AsyncSession, ticket_id: int, status: TicketStatus) -> Ticket:
    ticket = await get_or_404(db, ticket_id)
    ticket.status = status
    await db.flush()
    return ticket


async def list_tickets(
    db: AsyncSession,
    *,
    status: TicketStatus | None = None,
    user_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    stmt = select(Ticket)
    count_stmt = select(func.count()).select_from(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
        count_stmt = count_stmt.where(Ticket.status == status)
    if user_id is not None:
        stmt = stmt.where(Ticket.user_id == user_id)
        count_stmt = count_stmt.where(Ticket.user_id == user_id)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(stmt.order_by(Ticket.last_message_at.desc()).limit(limit).offset(offset))
    return list(rows.scalars().all()), total


async def open_count(db: AsyncSession) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(Ticket)
            .where(Ticket.status.in_([TicketStatus.open, TicketStatus.pending]))
        )
    ).scalar_one()
