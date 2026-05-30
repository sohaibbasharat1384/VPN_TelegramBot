"""Support tickets: create, list, reply."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import texts
from app.bot.customer.keyboards import tickets_menu_kb
from app.bot.customer.states import NewTicket, TicketReply
from app.models.enums import SenderType, TicketStatus
from app.models.user import User
from app.services import admin_service, ticket_service

router = Router()


@router.message(F.text == texts.BTN_TICKETS)
async def tickets_menu(message: Message) -> None:
    await message.answer(texts.TICKETS_MENU, reply_markup=tickets_menu_kb())


@router.callback_query(F.data == "ticket:new")
async def ticket_new(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NewTicket.subject)
    await callback.message.answer(texts.ENTER_TICKET_SUBJECT)
    await callback.answer()


@router.message(NewTicket.subject)
async def ticket_subject(message: Message, state: FSMContext) -> None:
    await state.update_data(subject=message.text.strip()[:160])
    await state.set_state(NewTicket.body)
    await message.answer(texts.ENTER_TICKET_BODY)


@router.message(NewTicket.body)
async def ticket_body(message: Message, db: AsyncSession, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    attachment = message.photo[-1].file_id if message.photo else None
    body = message.text or message.caption or "—"
    ticket = await ticket_service.create_ticket(
        db, user_id=user.id, subject=data["subject"], body=body, attachment_path=attachment
    )
    await state.clear()
    await message.answer(texts.TICKET_CREATED.format(id=ticket.id))
    await admin_service.notify_admins(
        db, f"🎫 تیکت جدید #{ticket.id}\nموضوع: {ticket.subject}\nکاربر: {user.display_name}"
    )


@router.callback_query(F.data == "ticket:list")
async def ticket_list(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    tickets, _ = await ticket_service.list_tickets(db, user_id=user.id, limit=20)
    if not tickets:
        await callback.answer(texts.NO_TICKETS, show_alert=True)
        return
    b = InlineKeyboardBuilder()
    for t in tickets:
        status = texts.STATUS_FA.get(t.status.value, t.status.value)
        b.row_width = 1
        from aiogram.types import InlineKeyboardButton

        b.row(
            InlineKeyboardButton(
                text=texts.TICKET_ROW.format(id=t.id, subject=t.subject, status=status),
                callback_data=f"ticket:open:{t.id}",
            )
        )
    await callback.message.answer("📂 تیکت‌های شما:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:open:"))
async def ticket_open(callback: CallbackQuery, db: AsyncSession, user: User) -> None:
    ticket_id = int(callback.data.split(":")[2])
    ticket = await ticket_service.get_or_404(db, ticket_id, with_messages=True)
    if ticket.user_id != user.id:
        await callback.answer("دسترسی ندارید.", show_alert=True)
        return
    lines = [f"🎫 تیکت #{ticket.id} — {ticket.subject}\n"]
    for m in ticket.messages:
        who = "شما" if m.sender_type == SenderType.user else "پشتیبانی"
        lines.append(f"<b>{who}:</b> {m.body}")
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder as KB

    b = KB()
    if ticket.status != TicketStatus.closed:
        b.row(InlineKeyboardButton(text="✍️ پاسخ", callback_data=f"ticket:reply:{ticket.id}"))
    await callback.message.answer("\n".join(lines), reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("ticket:reply:"))
async def ticket_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    ticket_id = int(callback.data.split(":")[2])
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(TicketReply.body)
    await callback.message.answer(texts.TICKET_REPLY_PROMPT.format(id=ticket_id))
    await callback.answer()


@router.message(TicketReply.body)
async def ticket_reply_body(message: Message, db: AsyncSession, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    ticket_id = data["reply_ticket_id"]
    await ticket_service.reply(
        db, ticket_id=ticket_id, body=message.text or "—",
        sender_type=SenderType.user, sender_user_id=user.id,
        attachment_path=message.photo[-1].file_id if message.photo else None,
    )
    await state.clear()
    await message.answer(texts.TICKET_REPLY_SENT)
    await admin_service.notify_admins(db, f"💬 پاسخ جدید کاربر در تیکت #{ticket_id}")
