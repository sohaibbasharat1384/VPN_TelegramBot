"""FSM states for admin bot flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ReviewNote(StatesGroup):
    note = State()


class UserSearch(StatesGroup):
    query = State()


class WalletAdjust(StatesGroup):
    amount = State()


class TicketReply(StatesGroup):
    body = State()


class AddConfig(StatesGroup):
    url = State()
    raw = State()


class NewCoupon(StatesGroup):
    code = State()
    value = State()


class NewCard(StatesGroup):
    number = State()
    holder = State()
    bank = State()


class Broadcast(StatesGroup):
    content = State()
