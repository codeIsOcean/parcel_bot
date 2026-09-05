import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import (
    BOT_TOKEN, LOG_LEVEL, REDIS_URL,
    USE_WEBHOOK, WEBHOOK_PATH, WEBHOOK_PORT, WEBHOOK_SECRET, WEBHOOK_URL,
)
from bot.handlers import main_router
from bot.middlewares.db import DatabaseMiddleware
from bot.utils.screen_manager import init_screen_storage

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    """Точка входа — запуск бота."""
    logger.info("[BOT] Запуск Parcel Bot...")

    # Создаём бота с HTML разметкой по умолчанию
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM storage (RedisStorage для prod, MemoryStorage как fallback)
    try:
        from aiogram.fsm.storage.redis import RedisStorage
        storage = RedisStorage.from_url(REDIS_URL) if REDIS_URL else MemoryStorage()
        logger.info("[BOT] FSM storage: %s", "Redis" if REDIS_URL else "Memory")
    except ImportError:
        storage = MemoryStorage()
        logger.warning("[BOT] redis not installed, using MemoryStorage")

    # Инициализируем Redis-хранилище для ScreenManager
    await init_screen_storage(REDIS_URL)

    # Диспетчер
    dp = Dispatcher(storage=storage)

    # Middleware для БД сессий
    dp.update.middleware(DatabaseMiddleware())

    # Подключаем все роутеры
    dp.include_router(main_router)

    try:
        if USE_WEBHOOK:
            await _run_webhook(bot, dp)
        else:
            await _run_polling(bot, dp)
    finally:
        await bot.session.close()
        logger.info("[BOT] Parcel Bot остановлен")


async def _run_polling(bot: Bot, dp: Dispatcher):
    """Запасной режим: long polling. Не выдерживает двух процессов на токене."""
    # Снимаем вебхук, иначе Telegram не отдаст апдейты через getUpdates
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("[BOT] Parcel Bot запущен, polling...")
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher):
    """Рабочий режим: Telegram сам стучится в наш адрес."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    # Без публичного адреса вебхук зарегистрировать нельзя — падаем явно
    if not WEBHOOK_URL:
        raise RuntimeError("USE_WEBHOOK=true, но BOT_WEBHOOK_URL не задан")

    # Регистрируем адрес в Telegram вместе с секретом, которым он подпишет запросы
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET or None,
        drop_pending_updates=True,
    )
    logger.info("[BOT] Webhook зарегистрирован: %s", WEBHOOK_URL)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET or None,
    ).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=WEBHOOK_PORT)
    await site.start()
    logger.info("[BOT] Parcel Bot слушает вебхук на порту %s, путь %s", WEBHOOK_PORT, WEBHOOK_PATH)

    try:
        # Держим процесс живым, обработку ведёт aiohttp
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
