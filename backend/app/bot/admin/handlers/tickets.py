"""Admin ticket management: list open, view, reply, close."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.admin.states import TicketReply
from app.core.config import settings
from app.core.permissions import Perm
from app.models.enums import SenderType, TicketStatus
from app.models.rbac import AdminUser
from app.models.user import User
from app.services import ticket_service
from app.utils.telegram import send_message

router = Router()


@router.message(F.text == texts.BTN_TICKETS)
async def list_open(message: Message, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.TICKETS_VIEW):
        return
    tickets, _ = await ticket_service.list_tickets(db, status=TicketStatus.pending, limit=20)
    tickets2, _ = await ticket_service.list_tickets(db, status=TicketStatus.open, limit=20)
    all_t = {t.id: t for t in [*tickets, *tickets2]}.values()
    if not all_t:
        await message.answer(texts.NO_OPEN_TICKETS)
        return
    from aiogram.types import InlineKeyboardButton

    b = InlineKeyboardBuilder()
    for t in all_t:
        b.row(InlineKeyboardButton(text=f"#{t.id} — {t.subject}", callback_data=f"tk:open:{t.id}"))
    await message.answer("🎫 تیکت‌های باز:", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("tk:open:"))
async def view_ticket(callback: CallbackQuery, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.TICKETS_VIEW):
        return
    ticket_id = int(callback.data.split(":")[2])
    ticket = await ticket_service.get_or_404(db, ticket_id, with_messages=True)
    body = "\n".join(
        f"{'👤' if m.sender_type == SenderType.user else '🛠'} {m.body}" for m in ticket.messages
    )
    status = texts_status(ticket.status)
    await callback.message.answer(
        texts.TICKET_VIEW.format(id=ticket.id, subject=ticket.subject, status=status, body=body),
        reply_markup=keyboards.ticket_actions_kb(ticket.id),
    )
    await callback.answer()


def texts_status(status: TicketStatus) -> str:
    from app.bot.common.texts import STATUS_FA

    return STATUS_FA.get(status.value, status.value)


@router.callback_query(F.data.startswith("tk:reply:"))
async def reply_start(callback: CallbackQuery, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.TICKETS_REPLY):
        return
    ticket_id = int(callback.data.split(":")[2])
    await state.update_data(reply_ticket=ticket_id)
    await state.set_state(TicketReply.body)
    await callback.message.answer(texts.ENTER_REPLY.format(id=ticket_id))
    await callback.answer()


@router.message(TicketReply.body)
async def reply_body(message: Message, db: AsyncSession, admin: AdminUser, state: FSMContext) -> None:
    data = await state.get_data()
    ticket_id = data["reply_ticket"]
    await state.clear()
    await ticket_service.reply(
        db, ticket_id=ticket_id, body=message.text or "—",
        sender_type=SenderType.admin, sender_admin_id=admin.id,
    )
    await db.commit()
    ticket = await ticket_service.get_or_404(db, ticket_id)
    user = await db.get(User, ticket.user_id)
    if user:
        await send_message(
            settings.customer_bot_token, user.telegram_id,
            f"💬 پاسخ جدید برای تیکت #{ticket_id}:\n\n{message.text}",
        )
    await message.answer(texts.REPLY_SENT)


@router.callback_query(F.data.startswith("tk:close:"))
async def close_ticket(callback: CallbackQuery, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.TICKETS_REPLY):
        return
    ticket_id = int(callback.data.split(":")[2])
    await ticket_service.set_status(db, ticket_id, TicketStatus.closed)
    await db.commit()
    await callback.answer(texts.DONE)
    await callback.message.edit_reply_markup(reply_markup=None)
