"""Общие фикстуры тестов.

База поднимается в памяти на SQLite, чтобы тесты не требовали Postgres
и не зависели от состояния стенда.
"""

import asyncio
import os

import pytest
import pytest_asyncio

# Токен принудительно пустой: тесты не должны стучаться в реальный Telegram,
# даже если в окружении контейнера настоящий BOT_TOKEN.
os.environ["BOT_TOKEN"] = ""
os.environ["FREE_ACCESS_UNTIL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.models.base import Base
# Импорт всех моделей нужен, чтобы Base.metadata знала про таблицы
from shared.models import (  # noqa: F401
    balance, chat, city, flight, match, message, parcel, payment, promo_chat,
    report, review, route_vote, subscription, user,
)


@pytest.fixture(scope="session")
def event_loop():
    """Один event loop на всю сессию тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Чистая база на каждый тест."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()
