import logging

from aiogram import Bot, Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import user_service
from bot.keyboards.main_kb import get_role_keyboard, get_sender_menu, get_traveler_menu
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager
from shared.models.user import UserRole

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Команда /start — приветствие и выбор роли."""
    # Очищаем FSM при /start (предотвращаем State Leak)
    await state.clear()

    # Получаем или создаём пользователя в БД
    user, created = await user_service.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_premium=message.from_user.is_premium or False,
    )

    lang = user.lang
    screen = ScreenManager(bot)

    if created:
        # Новый пользователь — показываем приветствие и выбор роли
        logger.info("[BOT] Новый пользователь: %s (%s)", user.full_name, user.id)
        await screen.show(
            message.from_user.id,
            t(lang, "start_welcome"),
            slot="inline",
            reply_markup=get_role_keyboard(lang),
        )
    else:
        # Существующий пользователь — показываем меню по роли
        logger.info("[BOT] Возврат пользователя: %s (%s)", user.full_name, user.id)
        if user.role in (UserRole.TRAVELER, UserRole.BOTH):
            await screen.show(
                message.from_user.id,
                t(lang, "start_welcome"),
                slot="main",
                reply_markup=get_traveler_menu(lang),
            )
        else:
            await screen.show(
                message.from_user.id,
                t(lang, "start_welcome"),
                slot="main",
                reply_markup=get_sender_menu(lang),
            )


@router.callback_query(F.data.startswith("role:"))
async def on_role_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Callback — пользователь выбрал роль."""
    # Очищаем FSM при выборе роли (предотвращаем State Leak)
    await state.clear()
    role_str = callback.data.split(":")[1]
    user, _ = await user_service.get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Обновляем роль пользователя
    new_role = UserRole.TRAVELER if role_str == "traveler" else UserRole.SENDER
    await user_service.update_user(session, user, role=new_role)

    logger.info("[BOT] Роль выбрана: user=%s, role=%s", user.id, role_str)

    # Удаляем сообщение с кнопками выбора роли
    await screen.delete_slot(callback.from_user.id, "inline")

    # Показываем меню по роли
    if role_str == "traveler":
        await screen.show(
            callback.from_user.id,
            t(lang, "start_welcome"),
            slot="main",
            reply_markup=get_traveler_menu(lang),
        )
    else:
        await screen.show(
            callback.from_user.id,
            t(lang, "start_welcome"),
            slot="main",
            reply_markup=get_sender_menu(lang),
        )

    await callback.answer()
