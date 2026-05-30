"""FSM states for customer bot multi-step flows."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ChargeWallet(StatesGroup):
    amount = State()
    tracking = State()
    receipt = State()


class CouponFlow(StatesGroup):
    code = State()


class CardOrderFlow(StatesGroup):
    tracking = State()
    receipt = State()


class NewTicket(StatesGroup):
    subject = State()
    body = State()


class TicketReply(StatesGroup):
    body = State()
