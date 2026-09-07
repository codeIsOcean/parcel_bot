"""Белый список сообщений в личке: бот не ведёт диалогов.

Пропускаем команды, контакт, оплату и шаги, где бот сам ждёт ответ
(онбординг, ответ поддержки). Всё остальное получает кнопку «Открыть
приложение» и до хендлеров не доходит.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)


def is_allowed(text: str | None, has_contact: bool, has_payment: bool, state: str | None) -> bool:
    """Чистое правило пропуска — вынесено ради тестов."""
    if has_contact or has_payment:
        return True
    # Бот ждёт ответ (онбординг, ответ поддержки) — пропускаем
    if state:
        return True
    return bool(text and text.startswith("/"))


class DormantGate(BaseMiddleware):
    """Короткое замыкание лишних сообщений на кнопку приложения."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        # Группы обслуживает свой роутер — там правило не действует
        if event.chat.type != "private":
            return await handler(event, data)

        fsm = data.get("state")
        state = await fsm.get_state() if fsm else None

        if is_allowed(event.text, bool(event.contact), bool(event.successful_payment), state):
            return await handler(event, data)

        # Лишнее сообщение: отвечаем кнопкой и не идём дальше
        from backend.app.services import user_service
        from bot.handlers.start import show_open_app

        session = data.get("session")
        if session is None:
            return None
        user, _ = await user_service.get_or_create_user(
            session, telegram_id=event.from_user.id, first_name=event.from_user.first_name,
        )
        await show_open_app(data["bot"], user, text_key="not_here")
        return None
