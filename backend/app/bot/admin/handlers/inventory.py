"""Admin inventory: counts and adding manual configs."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.admin.states import AddConfig
from app.core.permissions import Perm
from app.models.enums import ActorType
from app.models.rbac import AdminUser
from app.services import audit, inventory_service, plan_service

router = Router()


@router.message(F.text == texts.BTN_INVENTORY)
async def inventory_overview(message: Message, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.INVENTORY_VIEW):
        return
    counts = await inventory_service.counts_by_plan(db)
    plans = await plan_service.list_all(db)
    lines = [texts.INVENTORY_HEADER]
    for plan in plans:
        c = counts.get(plan.id, {})
        lines.append(
            texts.INVENTORY_ROW.format(
                title=plan.title, available=c.get("available", 0), sold=c.get("sold", 0)
            )
        )
    await message.answer("\n".join(lines), reply_markup=keyboards.add_config_kb())


@router.callback_query(F.data == "inv:add")
async def add_choose_plan(callback: CallbackQuery, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.INVENTORY_MANAGE):
        return
    plans = await plan_service.list_all(db)
    await callback.message.answer(
        texts.CHOOSE_PLAN_FOR_CONFIG, reply_markup=keyboards.plans_kb(plans, "inv:plan")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("inv:plan:"))
async def add_plan_selected(callback: CallbackQuery, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.INVENTORY_MANAGE):
        return
    plan_id = int(callback.data.split(":")[2])
    await state.update_data(config_plan=plan_id)
    await state.set_state(AddConfig.url)
    await callback.message.answer(texts.ENTER_CONFIG_URL)
    await callback.answer()


@router.message(AddConfig.url)
async def add_url(message: Message, state: FSMContext) -> None:
    await state.update_data(config_url=message.text.strip())
    await state.set_state(AddConfig.raw)
    await message.answer(texts.ENTER_CONFIG_RAW)


@router.message(AddConfig.raw)
async def add_raw(message: Message, db: AsyncSession, admin: AdminUser, state: FSMContext) -> None:
    data = await state.get_data()
    plan_id = data["config_plan"]
    await state.clear()
    config = await inventory_service.add_config(
        db, plan_id=plan_id, subscription_url=data["config_url"], raw_config=message.text.strip()
    )
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="inventory.add",
        target_type="config", target_id=config.id, new_value={"plan_id": plan_id},
    )
    await db.commit()
    plan = await plan_service.get_or_404(db, plan_id)
    await message.answer(texts.CONFIG_ADDED.format(title=plan.title))
