"""Start, main menu, and cancel handlers."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import texts
from app.bot.customer import keyboards
from app.models.user import User
from app.services import referral_service, user_service

router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_ref(
    message: Message, command: CommandObject, db: AsyncSession, user: User, user_created: bool
) -> None:
    # Deep-link payload carries the referrer's code: t.me/bot?start=CODE
    payload = (command.args or "").strip()
    if user.referred_by_id is None and payload:
        referrer = await user_service.get_by_referral_code(db, payload)
        if referrer and referrer.id != user.id:
            user.referred_by_id = referrer.id
            await db.flush()
            await referral_service.ensure_referral(db, user)
    await _greet(message, user)


@router.message(CommandStart())
async def start(message: Message, user: User) -> None:
    await _greet(message, user)


async def _greet(message: Message, user: User) -> None:
    await message.answer(
        texts.WELCOME.format(name=user.first_name or "کاربر"),
        reply_markup=keyboards.main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == texts.BTN_CANCEL)
@router.message(F.text == texts.BTN_MAIN_MENU)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.MAIN_MENU, reply_markup=keyboards.main_menu())
