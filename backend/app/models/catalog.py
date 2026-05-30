"""Catalog: panels (integration endpoints), plans, and manual-inventory configs."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import ConfigStatus, FulfilmentMode, PanelType


class Panel(PKMixin, TimestampMixin, Base):
    __tablename__ = "panels"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[PanelType] = mapped_column(Enum(PanelType, name="panel_type"), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted at rest
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)  # inbound/flow templates

    plans: Mapped[list[Plan]] = relationship(back_populates="panel")


class Plan(PKMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    title: Mapped[str] = mapped_column(String(128), nullable=False)
    data_limit_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Toman
    fulfilment_mode: Mapped[FulfilmentMode] = mapped_column(
        Enum(FulfilmentMode, name="fulfilment_mode"), default=FulfilmentMode.manual
    )
    panel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("panels.id", ondelete="RESTRICT")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    panel: Mapped[Panel | None] = relationship(back_populates="plans")
    configs: Mapped[list[Config]] = relationship(back_populates="plan")

    @property
    def data_limit_bytes(self) -> int:
        return self.data_limit_gb * 1024**3


class Config(PKMixin, Base):
    """A ready-to-sell V2Ray config in manual inventory."""

    __tablename__ = "configs"
    __table_args__ = (
        Index("ix_configs_plan_status", "plan_id", "status"),
    )

    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    subscription_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_config: Mapped[str] = mapped_column(Text, nullable=False)
    remark: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[ConfigStatus] = mapped_column(
        Enum(ConfigStatus, name="config_status"), default=ConfigStatus.available, index=True
    )
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reserved_order_id: Mapped[int | None] = mapped_column(BigInteger)
    sold_to_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plan: Mapped[Plan] = relationship(back_populates="configs")
