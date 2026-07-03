from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from backend.app.database import async_session


class DatabaseMiddleware(BaseMiddleware):
    """Middleware — инжектирует async-сессию БД в каждый handler."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Создаём сессию для каждого update
        async with async_session() as session:
            # Передаём сессию в handler через data
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception:
                # При ошибке — откатываем транзакцию
                await session.rollback()
                raise
