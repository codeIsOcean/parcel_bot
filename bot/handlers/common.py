"""Запасные обработчики: неизвестная команда и глобальная отмена."""

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import user_service
from bot.handlers.start import show_open_app
from bot.utils.screen_manager import ScreenManager

logger = logging.getLogger(__name__)
router = Router(name="common")


@router.callback_query(F.data == "cancel")
async def on_cancel_global(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Кнопка «Отмена» — выход из любого состояния."""
    await state.clear()
    await ScreenManager(bot).delete_slot(callback.from_user.id, "inline")
    await callback.answer()


@router.message()
async def on_unknown(message: Message, session: AsyncSession, bot: Bot):
    """Неизвестная команда — кнопка приложения."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    await show_open_app(bot, user, text_key="not_here")
