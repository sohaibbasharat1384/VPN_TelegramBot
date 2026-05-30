"""System-level tables: broadcasts, audit logs, notifications, settings."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import (
    ActorType,
    BroadcastStatus,
    BroadcastTarget,
    ContentType,
    NotificationKind,
)


class Broadcast(PKMixin, TimestampMixin, Base):
    __tablename__ = "broadcasts"

    admin_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType, name="content_type"))
    body: Mapped[str] = mapped_column(Text, default="")
    media_path: Mapped[str | None] = mapped_column(Text)
    target: Mapped[BroadcastTarget] = mapped_column(Enum(BroadcastTarget, name="broadcast_target"))
    target_user_ids: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))
    status: Mapped[BroadcastStatus] = mapped_column(
        Enum(BroadcastStatus, name="broadcast_status"), default=BroadcastStatus.queued
    )
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(PKMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_actor_created", "actor_id", "created_at"),
        Index("ix_audit_target", "target_type", "target_id"),
    )

    actor_type: Mapped[ActorType] = mapped_column(Enum(ActorType, name="actor_type"))
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(48))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    ip_address: Mapped[str | None] = mapped_column(INET)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Notification(PKMixin, Base):
    """Outbound message log; the unique constraint de-duplicates alerts."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "reference_id", name="uq_notification_dedupe"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[NotificationKind] = mapped_column(Enum(NotificationKind, name="notification_kind"))
    reference_id: Mapped[int] = mapped_column(BigInteger, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Setting(Base):
    """Key/value application configuration, editable from the dashboard."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
