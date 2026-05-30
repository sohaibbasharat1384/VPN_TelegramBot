"""Admin coupon management: list, create, toggle."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.admin import guards, keyboards, texts
from app.bot.admin.states import NewCoupon
from app.core.exceptions import CouponError
from app.core.permissions import Perm
from app.models.coupon import Coupon
from app.models.enums import ActorType, DiscountType
from app.models.rbac import AdminUser
from app.services import audit, coupon_service
from app.utils.formatting import to_fa_digits, toman

router = Router()


@router.message(F.text == texts.BTN_COUPONS)
async def list_coupons(message: Message, db: AsyncSession, perms: set[str]) -> None:
    if not await guards.ensure(message, perms, Perm.COUPONS_MANAGE):
        return
    coupons = (await db.execute(select(Coupon).order_by(Coupon.created_at.desc()))).scalars().all()
    if not coupons:
        await message.answer(texts.NO_COUPONS, reply_markup=keyboards.new_coupon_kb())
        return
    lines = []
    for c in coupons:
        if c.discount_type == DiscountType.percent:
            value = f"{to_fa_digits(c.discount_value)}٪"
        else:
            value = toman(c.discount_value)
        status = "فعال" if c.is_active else "غیرفعال"
        lines.append(
            texts.COUPON_ROW.format(
                code=c.code, value=value, uses=to_fa_digits(c.used_count), status=status
            )
        )
    await message.answer("\n".join(lines), reply_markup=keyboards.new_coupon_kb())


@router.callback_query(F.data == "coupon:new")
async def new_coupon(callback: CallbackQuery, state: FSMContext, perms: set[str]) -> None:
    if not await guards.ensure(callback, perms, Perm.COUPONS_MANAGE):
        return
    await state.set_state(NewCoupon.code)
    await callback.message.answer(texts.ENTER_COUPON_CODE)
    await callback.answer()


@router.message(NewCoupon.code)
async def coupon_code(message: Message, state: FSMContext) -> None:
    await state.update_data(code=message.text.strip().upper())
    await message.answer(texts.ENTER_COUPON_TYPE, reply_markup=keyboards.coupon_type_kb())


@router.callback_query(F.data.startswith("coupon:type:"))
async def coupon_type(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(disc_type=callback.data.split(":")[2])
    await state.set_state(NewCoupon.value)
    await callback.message.answer(texts.ENTER_COUPON_VALUE)
    await callback.answer()


@router.message(NewCoupon.value)
async def coupon_value(message: Message, db: AsyncSession, admin: AdminUser, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", "")
    if not raw.isdigit():
        await message.answer(texts.ENTER_COUPON_VALUE)
        return
    data = await state.get_data()
    await state.clear()
    dtype = DiscountType(data["disc_type"])
    try:
        coupon = await coupon_service.create(
            db, code=data["code"], discount_type=dtype, discount_value=int(raw)
        )
    except CouponError as exc:
        await message.answer(exc.user_message)
        return
    await audit.record(
        db, actor_type=ActorType.admin, actor_id=admin.id, action="coupon.create",
        target_type="coupon", target_id=coupon.id, new_value={"code": coupon.code},
    )
    await db.commit()
    await message.answer(texts.COUPON_CREATED.format(code=coupon.code))
