"""Admin bot keyboards."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.admin import texts
from app.models.catalog import Plan


def main_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=texts.BTN_PAYMENTS), KeyboardButton(text=texts.BTN_STATS))
    b.row(KeyboardButton(text=texts.BTN_USERS), KeyboardButton(text=texts.BTN_TICKETS))
    b.row(KeyboardButton(text=texts.BTN_INVENTORY), KeyboardButton(text=texts.BTN_COUPONS))
    b.row(KeyboardButton(text=texts.BTN_CARDS), KeyboardButton(text=texts.BTN_BROADCAST))
    return b.as_markup(resize_keyboard=True)


def review_kb(payment_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=texts.BTN_APPROVE, callback_data=f"pay:approve:{payment_id}"),
        InlineKeyboardButton(text=texts.BTN_REJECT, callback_data=f"pay:reject:{payment_id}"),
    )
    return b.as_markup()


def user_actions_kb(user_id: int, *, banned: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    ban_btn = (
        InlineKeyboardButton(text=texts.BTN_UNBAN, callback_data=f"user:unban:{user_id}")
        if banned
        else InlineKeyboardButton(text=texts.BTN_BAN, callback_data=f"user:ban:{user_id}")
    )
    b.row(ban_btn)
    b.row(InlineKeyboardButton(text=texts.BTN_ADJUST, callback_data=f"user:adjust:{user_id}"))
    return b.as_markup()


def ticket_actions_kb(ticket_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=texts.BTN_REPLY, callback_data=f"tk:reply:{ticket_id}"),
        InlineKeyboardButton(text=texts.BTN_CLOSE, callback_data=f"tk:close:{ticket_id}"),
    )
    return b.as_markup()


def plans_kb(plans: list[Plan], prefix: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for plan in plans:
        b.row(InlineKeyboardButton(text=plan.title, callback_data=f"{prefix}:{plan.id}"))
    return b.as_markup()


def add_config_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_ADD_CONFIG, callback_data="inv:add"))
    return b.as_markup()


def new_coupon_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_NEW_COUPON, callback_data="coupon:new"))
    return b.as_markup()


def coupon_type_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="درصدی", callback_data="coupon:type:percent"),
        InlineKeyboardButton(text="مبلغی", callback_data="coupon:type:fixed"),
    )
    return b.as_markup()


def cards_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_NEW_CARD, callback_data="card:new"))
    return b.as_markup()


def broadcast_target_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_TARGET_ALL, callback_data="bc:target:all"))
    b.row(InlineKeyboardButton(text=texts.BTN_TARGET_ACTIVE, callback_data="bc:target:active"))
    return b.as_markup()
