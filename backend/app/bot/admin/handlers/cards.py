"""Admin card-to-card destination management."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.admin.states import NewCard
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.services import audit, payment_service

router = Router()


@router.message(F.text == texts.BTN_CARDS)
async def list_cards(message: Message, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.CARDS_MANAGE):
        return
    cards = await payment_service.active_cards(db)
    if not cards:
        await message.answer(texts.NO_CARDS, reply_markup=keyboards.cards_kb())
        return
    lines = [
        texts.CARD_ROW.format(bank=c.bank_name, number=c.card_number, holder=c.card_holder,
                              status="فعال" if c.is_active else "غیرفعال")
        for c in cards
    ]
    await message.answer("\n".join(lines), reply_markup=keyboards.cards_kb())


@router.callback_query(F.data == "card:new")
async def new_card(callback: CallbackQuery, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.CARDS_MANAGE):
        return
    await state.set_state(NewCard.number)
    await callback.message.answer(texts.ENTER_CARD_NUMBER)
    await callback.answer()


@router.message(NewCard.number)
async def card_number(message: Message, state: FSMContext) -> None:
    await state.update_data(number=message.text.strip())
    await state.set_state(NewCard.holder)
    await message.answer(texts.ENTER_CARD_HOLDER)


@router.message(NewCard.holder)
async def card_holder(message: Message, state: FSMContext) -> None:
    await state.update_data(holder=message.text.strip())
    await state.set_state(NewCard.bank)
    await message.answer(texts.ENTER_CARD_BANK)


@router.message(NewCard.bank)
async def card_bank(message: Message, db: AsyncSession, admin: AdminUser, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    from app.models.order import PaymentCard

    card = PaymentCard(
        card_number=data["number"], card_holder=data["holder"], bank_name=message.text.strip()
    )
    db.add(card)
    await db.flush()
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="card.create",
        target_type="card", target_id=card.id, new_value={"bank": card.bank_name},
    )
    await db.commit()
    await message.answer(texts.CARD_ADDED)
