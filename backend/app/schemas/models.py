"""Read/write schemas for the dashboard API."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.enums import (
    DiscountType,
    FulfilmentMode,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    SubscriptionStatus,
    TicketStatus,
)
from app.schemas.base import APIModel, ORMModel


# ---------- Users ----------
class UserRead(ORMModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    is_banned: bool
    referral_code: str
    referred_by_id: int | None
    created_at: datetime


class UserDetail(UserRead):
    balance: int = 0


class BanRequest(APIModel):
    banned: bool
    reason: str | None = None


class WalletAdjustRequest(APIModel):
    delta: int
    description: str = Field(min_length=1, max_length=200)


# ---------- Plans ----------
class PlanRead(ORMModel):
    id: int
    title: str
    data_limit_gb: int
    duration_days: int
    price: int
    fulfilment_mode: FulfilmentMode
    panel_id: int | None
    is_active: bool
    sort_order: int


class PlanCreate(APIModel):
    title: str
    data_limit_gb: int = Field(ge=1)
    duration_days: int = Field(ge=1, default=30)
    price: int = Field(ge=0)
    fulfilment_mode: FulfilmentMode = FulfilmentMode.manual
    panel_id: int | None = None
    sort_order: int = 0


class PlanUpdate(APIModel):
    title: str | None = None
    data_limit_gb: int | None = Field(default=None, ge=1)
    duration_days: int | None = Field(default=None, ge=1)
    price: int | None = Field(default=None, ge=0)
    fulfilment_mode: FulfilmentMode | None = None
    panel_id: int | None = None
    is_active: bool | None = None
    sort_order: int | None = None


# ---------- Inventory ----------
class ConfigCreate(APIModel):
    plan_id: int
    subscription_url: str
    raw_config: str
    remark: str | None = None


class InventoryCount(APIModel):
    plan_id: int
    title: str
    available: int
    reserved: int
    sold: int
    low: bool


# ---------- Payments ----------
class PaymentRead(ORMModel):
    id: int
    user_id: int
    order_id: int | None
    purpose: PaymentPurpose
    method: PaymentMethod
    provider: str | None
    amount: int
    status: PaymentStatus
    tracking_number: str | None
    receipt_path: str | None
    admin_note: str | None
    created_at: datetime


class PaymentReviewRequest(APIModel):
    note: str | None = None


# ---------- Coupons ----------
class CouponRead(ORMModel):
    id: int
    code: str
    discount_type: DiscountType
    discount_value: int
    max_uses: int | None
    used_count: int
    per_user_limit: int
    min_order_amount: int
    expires_at: datetime | None
    is_active: bool


class CouponCreate(APIModel):
    code: str
    discount_type: DiscountType
    discount_value: int = Field(ge=1)
    max_uses: int | None = None
    per_user_limit: int = 1
    min_order_amount: int = 0
    expires_at: datetime | None = None


# ---------- Subscriptions ----------
class SubscriptionRead(ORMModel):
    id: int
    user_id: int
    plan_id: int
    subscription_url: str
    data_limit_bytes: int
    data_used_bytes: int
    starts_at: datetime
    expires_at: datetime
    status: SubscriptionStatus


# ---------- Tickets ----------
class TicketMessageRead(ORMModel):
    id: int
    sender_type: str
    body: str
    attachment_path: str | None
    created_at: datetime


class TicketRead(ORMModel):
    id: int
    user_id: int
    subject: str
    status: TicketStatus
    last_message_at: datetime
    created_at: datetime


class TicketDetail(TicketRead):
    messages: list[TicketMessageRead] = []


class TicketReplyRequest(APIModel):
    body: str = Field(min_length=1)


class TicketStatusRequest(APIModel):
    status: TicketStatus


# ---------- Cards ----------
class CardRead(ORMModel):
    id: int
    card_number: str
    card_holder: str
    bank_name: str
    is_active: bool
    sort_order: int


class CardCreate(APIModel):
    card_number: str
    card_holder: str
    bank_name: str
    sort_order: int = 0


# ---------- Settings ----------
class SettingUpdate(APIModel):
    key: str
    value: object
