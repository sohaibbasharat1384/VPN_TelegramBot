"""Enumerations used across the schema (mapped to native PostgreSQL enums)."""
from __future__ import annotations

import enum


class FulfilmentMode(str, enum.Enum):
    manual = "manual"
    panel = "panel"


class ConfigStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    sold = "sold"


class OrderKind(str, enum.Enum):
    new = "new"
    renewal = "renewal"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    awaiting_payment = "awaiting_payment"
    paid = "paid"
    delivered = "delivered"
    cancelled = "cancelled"
    expired = "expired"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    disabled = "disabled"


class PaymentPurpose(str, enum.Enum):
    order = "order"
    wallet_topup = "wallet_topup"


class PaymentMethod(str, enum.Enum):
    wallet = "wallet"
    card_to_card = "card_to_card"
    gateway = "gateway"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    failed = "failed"


class WalletTxnType(str, enum.Enum):
    topup = "topup"
    purchase = "purchase"
    refund = "refund"
    referral_reward = "referral_reward"
    admin_adjust = "admin_adjust"


class DiscountType(str, enum.Enum):
    percent = "percent"
    fixed = "fixed"


class ReferralStatus(str, enum.Enum):
    pending = "pending"
    qualified = "qualified"
    rewarded = "rewarded"


class TicketStatus(str, enum.Enum):
    open = "open"
    pending = "pending"
    answered = "answered"
    closed = "closed"


class TicketPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"


class SenderType(str, enum.Enum):
    user = "user"
    admin = "admin"


class BroadcastTarget(str, enum.Enum):
    all = "all"
    active = "active"
    specific = "specific"


class BroadcastStatus(str, enum.Enum):
    queued = "queued"
    sending = "sending"
    done = "done"
    failed = "failed"


class ContentType(str, enum.Enum):
    text = "text"
    photo = "photo"
    video = "video"
    file = "file"


class ActorType(str, enum.Enum):
    admin = "admin"
    system = "system"
    user = "user"


class PanelType(str, enum.Enum):
    marzban = "marzban"
    xui = "xui"


class NotificationKind(str, enum.Enum):
    usage_80 = "usage_80"
    usage_90 = "usage_90"
    usage_100 = "usage_100"
    expiry_7 = "expiry_7"
    expiry_3 = "expiry_3"
    expiry_1 = "expiry_1"
    expired = "expired"
    low_inventory = "low_inventory"
    generic = "generic"
