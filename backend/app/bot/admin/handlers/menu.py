"""Admin start menu + cancel."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.admin import keyboards, texts
from app.models.rbac import AdminUser

router = Router()


@router.message(CommandStart())
async def start(message: Message, admin: AdminUser) -> None:
    await message.answer(
        f"{texts.PANEL_TITLE}\nخوش آمدید {admin.full_name or ''} ({admin.role.name})",
        reply_markup=keyboards.main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == texts.BTN_CANCEL)
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())
