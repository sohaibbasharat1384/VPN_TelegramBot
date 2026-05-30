"""Customer bot entry point (long polling)."""
from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.common.middlewares import SessionUserMiddleware
from app.bot.customer.handlers import build_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger("customer_bot")


def create_dispatcher() -> Dispatcher:
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)
    dp.message.outer_middleware(SessionUserMiddleware())
    dp.callback_query.outer_middleware(SessionUserMiddleware())
    dp.include_router(build_router())
    return dp


async def main() -> None:
    configure_logging()
    if not settings.customer_bot_token:
        raise SystemExit("CUSTOMER_BOT_TOKEN is not set")
    bot = Bot(
        token=settings.customer_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("customer_bot.start")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
