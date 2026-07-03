import logging

from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import user_service
from bot.keyboards.main_kb import get_settings_keyboard, get_sender_menu, get_traveler_menu
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager
from shared.models.user import UserRole

logger = logging.getLogger(__name__)
router = Router(name="settings")


@router.message(F.text.contains("Настройки") | F.text.contains("Settings"), StateFilter(None))
async def on_settings(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Настройки' — показать меню настроек."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    await screen.show(
        message.from_user.id,
        t(lang, "settings_title"),
        slot="inline",
        reply_markup=get_settings_keyboard(lang),
    )


@router.callback_query(F.data.startswith("lang:"))
async def on_language_change(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Смена языка."""
    new_lang = callback.data.split(":")[1]
    screen = ScreenManager(bot)

    user, _ = await user_service.get_or_create_user(
        session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
    )

    # Обновляем язык в БД
    await user_service.update_user(session, user, lang=new_lang)

    # Обновляем inline-сообщение с настройками
    lang_name = "Русский" if new_lang == "ru" else "English"
    await screen.edit(
        callback.from_user.id,
        t(new_lang, "language_changed", lang=lang_name),
        slot="inline",
        reply_markup=get_settings_keyboard(new_lang),
    )

    # Обновляем reply-клавиатуру (меню) на новом языке
    if user.role in (UserRole.TRAVELER, UserRole.BOTH):
        kb = get_traveler_menu(new_lang)
    else:
        kb = get_sender_menu(new_lang)

    await screen.show(
        callback.from_user.id,
        t(new_lang, "start_welcome"),
        slot="main",
        reply_markup=kb,
    )

    await callback.answer(t(new_lang, "language_changed", lang=lang_name))
