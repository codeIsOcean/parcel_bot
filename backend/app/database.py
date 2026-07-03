from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.app.config import settings

# Создаём async engine (общий для всего приложения)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Фабрика async-сессий
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Dependency — получить async-сессию БД."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            # При ошибке — откатываем транзакцию
            await session.rollback()
            raise
