"""Orders, subscriptions, payments, and card-to-card destinations."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import (
    OrderKind,
    OrderStatus,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    SubscriptionStatus,
)


class Order(PKMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
        CheckConstraint(
            "final_price = original_price - discount_amount", name="final_price_consistent"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[OrderKind] = mapped_column(Enum(OrderKind, name="order_kind"))
    renew_subscription_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    original_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coupon_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("coupons.id", ondelete="SET NULL")
    )
    discount_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    final_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), default=OrderStatus.pending, index=True
    )

    payment: Mapped[Payment | None] = relationship(
        back_populates="order", uselist=False
    )
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="order", uselist=False, foreign_keys="Subscription.order_id"
    )


class Subscription(PKMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
        Index("ix_subscriptions_expires", "expires_at"),
        CheckConstraint(
            "(config_id IS NOT NULL) <> (panel_id IS NOT NULL)",
            name="exactly_one_fulfilment_source",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"))
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="RESTRICT"))
    config_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("configs.id", ondelete="SET NULL")
    )
    panel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("panels.id", ondelete="SET NULL")
    )
    panel_username: Mapped[str | None] = mapped_column(String(128))
    subscription_url: Mapped[str] = mapped_column(Text, nullable=False)
    data_limit_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.active,
        index=True,
    )
    usage_alert_level: Mapped[int] = mapped_column(SmallInteger, default=0)
    expiry_alerts_sent: Mapped[list[str]] = mapped_column(ARRAY(String(8)), default=list)

    order: Mapped[Order] = relationship(
        back_populates="subscription", foreign_keys=[order_id]
    )


class PaymentCard(PKMixin, TimestampMixin, Base):
    """Card-to-card destination accounts (editable from the admin panel)."""

    __tablename__ = "payment_cards"

    card_number: Mapped[str] = mapped_column(String(32), nullable=False)
    card_holder: Mapped[str] = mapped_column(String(128), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Payment(PKMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_status_created", "status", "created_at"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="SET NULL"), unique=True
    )
    purpose: Mapped[PaymentPurpose] = mapped_column(Enum(PaymentPurpose, name="payment_purpose"))
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"))
    provider: Mapped[str | None] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.pending
    )
    card_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("payment_cards.id", ondelete="SET NULL")
    )
    receipt_path: Mapped[str | None] = mapped_column(Text)
    tracking_number: Mapped[str | None] = mapped_column(String(64))
    gateway_authority: Mapped[str | None] = mapped_column(String(128), index=True)
    gateway_ref_id: Mapped[str | None] = mapped_column(String(128))
    reviewed_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    admin_note: Mapped[str | None] = mapped_column(Text)

    order: Mapped[Order | None] = relationship(back_populates="payment")
