"""Deliver a purchased subscription to the customer: link + QR image + raw config."""
from __future__ import annotations

from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.common import texts
from app.models.catalog import Config
from app.models.order import Subscription
from app.utils.formatting import gb, jalali
from app.utils.qr import make_qr_png


async def deliver_subscription(
    bot: Bot, chat_id: int, db: AsyncSession, subscription: Subscription
) -> None:
    volume = gb(subscription.data_limit_bytes // 1024**3)
    await bot.send_message(
        chat_id,
        texts.DELIVERED.format(
            url=subscription.subscription_url,
            expires=jalali(subscription.expires_at),
            volume=volume,
        ),
    )

    # QR of the subscription URL.
    png = make_qr_png(subscription.subscription_url)
    await bot.send_photo(
        chat_id,
        BufferedInputFile(png, filename="subscription_qr.png"),
        caption=texts.QR_CAPTION,
    )

    # Raw config text (from inventory config when available).
    raw = subscription.subscription_url
    if subscription.config_id:
        config = await db.get(Config, subscription.config_id)
        if config is not None:
            raw = config.raw_config
    await bot.send_message(chat_id, f"{texts.RAW_CONFIG_CAPTION}\n<code>{raw}</code>")
