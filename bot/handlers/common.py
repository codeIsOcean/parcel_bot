import logging

from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import user_service
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager

logger = logging.getLogger(__name__)
router = Router(name="common")


@router.callback_query(F.data == "cancel")
async def on_cancel_global(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Глобальная кнопка 'Отмена' — выход из любого FSM."""
    await state.clear()
    screen = ScreenManager(bot)
    await screen.delete_slot(callback.from_user.id, "inline")
    await callback.answer()


@router.message(StateFilter(None))
async def on_unknown_message(message: Message, session: AsyncSession, bot: Bot):
    """Catch-all — неизвестное сообщение вне FSM."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    text = t(lang, "unknown_command")

    await screen.show(message.from_user.id, text, slot="temp")
