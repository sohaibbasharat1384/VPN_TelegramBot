"""Import every model so SQLAlchemy's metadata is fully populated.

Alembic's ``env.py`` imports ``Base.metadata`` from here, so any new model
module must be imported below to be picked up by autogenerate.
"""
from app.db.base import Base
from app.models.catalog import Config, Panel, Plan
from app.models.coupon import Coupon, CouponRedemption
from app.models.enums import (
    ActorType,
    BroadcastStatus,
    BroadcastTarget,
    ConfigStatus,
    ContentType,
    DiscountType,
    FulfilmentMode,
    NotificationKind,
    OrderKind,
    OrderStatus,
    PanelType,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    ReferralStatus,
    SenderType,
    SubscriptionStatus,
    TicketPriority,
    TicketStatus,
    WalletTxnType,
)
from app.models.order import Order, Payment, PaymentCard, Subscription
from app.models.rbac import AdminUser, Permission, RefreshToken, Role, role_permissions
from app.models.referral import Referral, ReferralReward
from app.models.system import AuditLog, Broadcast, Notification, Setting
from app.models.ticket import Ticket, TicketMessage
from app.models.user import User, Wallet, WalletTransaction

__all__ = [
    "Base",
    "Panel",
    "Plan",
    "Config",
    "Coupon",
    "CouponRedemption",
    "Order",
    "Payment",
    "PaymentCard",
    "Subscription",
    "AdminUser",
    "Permission",
    "RefreshToken",
    "Role",
    "role_permissions",
    "Referral",
    "ReferralReward",
    "AuditLog",
    "Broadcast",
    "Notification",
    "Setting",
    "Ticket",
    "TicketMessage",
    "User",
    "Wallet",
    "WalletTransaction",
    # enums
    "ActorType",
    "BroadcastStatus",
    "BroadcastTarget",
    "ConfigStatus",
    "ContentType",
    "DiscountType",
    "FulfilmentMode",
    "NotificationKind",
    "OrderKind",
    "OrderStatus",
    "PanelType",
    "PaymentMethod",
    "PaymentPurpose",
    "PaymentStatus",
    "ReferralStatus",
    "SenderType",
    "SubscriptionStatus",
    "TicketPriority",
    "TicketStatus",
    "WalletTxnType",
]
