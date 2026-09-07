"""Реестр групп: бота добавили в чат или выгнали (my_chat_member).

Запись в реестре появляется сама, а включать рассылку и выбирать,
что публиковать, администратор будет в панели Mini App.
"""

import logging

from aiogram import Router
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import crosspost_service

logger = logging.getLogger(__name__)
router = Router(name="groups")


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, session: AsyncSession):
    """Обновить реестр по изменению членства бота."""
    chat = event.chat
    status = event.new_chat_member.status
    # Статус приходит enum-ом, сервису нужна строка
    status_value = getattr(status, "value", status)

    result = await crosspost_service.on_my_chat_member(
        session,
        {"id": chat.id, "type": chat.type, "title": chat.title, "username": chat.username},
        status_value,
        added_by=event.from_user.id if event.from_user else None,
    )
    if result:
        logger.info("[GROUPS] %s: chat=%s, member=%s", chat.title, chat.id, result.is_member)
