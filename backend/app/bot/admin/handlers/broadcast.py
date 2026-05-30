"""Admin broadcast: choose audience, compose, enqueue fan-out."""
from __future__ import annotations

import os
import uuid

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.admin.states import Broadcast as BroadcastState
from app.core.config import settings
from app.core.permissions import Perm
from app.models.enums import BroadcastTarget, ContentType
from app.models.rbac import AdminUser
from app.services import broadcast_service

router = Router()


@router.message(F.text == texts.BTN_BROADCAST)
async def broadcast_entry(message: Message, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.BROADCAST_SEND):
        return
    await message.answer(texts.BROADCAST_TARGET, reply_markup=keyboards.broadcast_target_kb())


@router.callback_query(F.data.startswith("bc:target:"))
async def broadcast_target(callback: CallbackQuery, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.BROADCAST_SEND):
        return
    target = callback.data.split(":")[2]
    await state.update_data(target=target)
    await state.set_state(BroadcastState.content)
    await callback.message.answer(texts.ENTER_BROADCAST)
    await callback.answer()


async def _save_media(bot: Bot, file_id: str, suffix: str) -> str:
    folder = os.path.join(settings.media_root, "broadcasts")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{uuid.uuid4().hex}{suffix}")
    await bot.download(file=file_id, destination=path)
    return path


@router.message(BroadcastState.content)
async def broadcast_compose(
    message: Message, db: AsyncSession, admin: AdminUser, state: FSMContext, bot: Bot
) -> None:
    data = await state.get_data()
    await state.clear()
    target = BroadcastTarget(data["target"])

    media_path: str | None = None
    body = message.caption or message.text or ""
    if message.photo:
        content_type = ContentType.photo
        media_path = await _save_media(bot, message.photo[-1].file_id, ".jpg")
    elif message.video:
        content_type = ContentType.video
        media_path = await _save_media(bot, message.video.file_id, ".mp4")
    elif message.document:
        content_type = ContentType.file
        media_path = await _save_media(bot, message.document.file_id,
                                       os.path.splitext(message.document.file_name or "")[1] or ".bin")
    else:
        content_type = ContentType.text

    broadcast = await broadcast_service.create(
        db, admin_id=admin.id, content_type=content_type, body=body,
        target=target, media_path=media_path,
    )
    await db.commit()

    # Enqueue fan-out on the worker (survives bot restarts, rate-limited).
    from app.workers.tasks import send_broadcast

    send_broadcast.delay(broadcast.id)
    await message.answer(texts.BROADCAST_QUEUED, reply_markup=keyboards.main_menu())
