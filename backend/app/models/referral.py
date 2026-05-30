"""Referral relationships and reward grants."""
from __future__ import annotations

from sqlalchemy import BigInteger, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin
from app.models.enums import ReferralStatus


class Referral(PKMixin, TimestampMixin, Base):
    __tablename__ = "referrals"

    referrer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referred_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[ReferralStatus] = mapped_column(
        Enum(ReferralStatus, name="referral_status"), default=ReferralStatus.pending
    )

    rewards: Mapped[list[ReferralReward]] = relationship(back_populates="referral")


class ReferralReward(PKMixin, TimestampMixin, Base):
    __tablename__ = "referral_rewards"

    referral_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False
    )
    referrer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wallet_transaction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("wallet_transactions.id", ondelete="SET NULL")
    )

    referral: Mapped[Referral] = relationship(back_populates="rewards")
