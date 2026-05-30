"""Telegram customers, wallets, and wallet transactions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import WalletTxnType


class User(PKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str] = mapped_column(String(8), default="fa")
    phone: Mapped[str | None] = mapped_column(String(32))
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    banned_reason: Mapped[str | None] = mapped_column(Text)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    referred_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    wallet: Mapped[Wallet] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    referred_by: Mapped[User | None] = relationship(remote_side="User.id")

    @property
    def display_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or (f"@{self.username}" if self.username else str(self.telegram_id))


class Wallet(PKMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="wallet")
    transactions: Mapped[list[WalletTransaction]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan"
    )


class WalletTransaction(PKMixin, Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (Index("ix_wallet_txn_wallet_created", "wallet_id", "created_at"),)

    wallet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # signed
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[WalletTxnType] = mapped_column(
        Enum(WalletTxnType, name="wallet_txn_type"), nullable=False
    )
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    wallet: Mapped[Wallet] = relationship(back_populates="transactions")
