"""Customer bot keyboards (Persian, RTL)."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.common import texts
from app.models.catalog import Plan
from app.utils.formatting import gb, toman


def main_menu() -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=texts.BTN_BUY), KeyboardButton(text=texts.BTN_RENEW))
    b.row(KeyboardButton(text=texts.BTN_WALLET), KeyboardButton(text=texts.BTN_MY_SUBS))
    b.row(KeyboardButton(text=texts.BTN_REFERRAL), KeyboardButton(text=texts.BTN_COUPON))
    b.row(KeyboardButton(text=texts.BTN_TICKETS))
    return b.as_markup(resize_keyboard=True)


def plans_kb(plans: list[Plan]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for plan in plans:
        label = f"{gb(plan.data_limit_gb)} — {toman(plan.price)}"
        b.row(InlineKeyboardButton(text=label, callback_data=f"buy:plan:{plan.id}"))
    return b.as_markup()


def payment_methods_kb(plan_id: int, *, has_coupon: bool, gateway_enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.PAY_WALLET, callback_data=f"buy:pay:wallet:{plan_id}"))
    b.row(InlineKeyboardButton(text=texts.PAY_CARD, callback_data=f"buy:pay:card:{plan_id}"))
    if gateway_enabled:
        b.row(InlineKeyboardButton(text=texts.PAY_GATEWAY, callback_data=f"buy:pay:gateway:{plan_id}"))
    coupon_label = texts.COUPON_CLEARED if has_coupon else texts.APPLY_COUPON
    b.row(InlineKeyboardButton(text=coupon_label, callback_data=f"buy:coupon:{plan_id}"))
    b.row(InlineKeyboardButton(text=texts.BTN_BACK, callback_data="buy:list"))
    return b.as_markup()


def charge_methods_kb(*, card_enabled: bool, gateway_enabled: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if card_enabled:
        b.row(InlineKeyboardButton(text=texts.PAY_CARD, callback_data="wallet:charge:card"))
    if gateway_enabled:
        b.row(InlineKeyboardButton(text=texts.PAY_GATEWAY, callback_data="wallet:charge:gateway"))
    return b.as_markup()


def wallet_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_CHARGE, callback_data="wallet:charge"))
    b.row(InlineKeyboardButton(text=texts.BTN_WALLET_HISTORY, callback_data="wallet:history"))
    return b.as_markup()


def tickets_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_NEW_TICKET, callback_data="ticket:new"))
    b.row(InlineKeyboardButton(text=texts.BTN_MY_TICKETS, callback_data="ticket:list"))
    return b.as_markup()


def renew_kb(subscription_id: int, plan_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text=texts.BTN_RENEW_THIS, callback_data=f"renew:do:{subscription_id}:{plan_id}"
        )
    )
    return b.as_markup()


def pay_now_kb(url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text=texts.BTN_PAY_NOW, url=url))
    return b.as_markup()
