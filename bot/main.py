import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, LOG_LEVEL, REDIS_URL
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

    # Удаляем webhook и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("[BOT] Parcel Bot запущен, polling...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("[BOT] Parcel Bot остановлен")


if __name__ == "__main__":
    asyncio.run(main())
