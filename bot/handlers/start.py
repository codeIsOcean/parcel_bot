"""Вход и онбординг: /start [payload] → язык → телефон → «Открыть приложение».

Бот — тонкая обёртка над Mini App. Здесь только то, что в приложении
сделать нельзя: получить номер телефона через контакт Telegram и дать
кнопку запуска. Payload из /start (parcel_12, flight_7, admin...) ведёт
на нужный экран приложения после регистрации.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import admin_service, user_service
from bot.keyboards.webapp_kb import contact_keyboard, language_keyboard, open_app_keyboard
from bot.utils.locale import SUPPORTED_LANGS, t
from bot.utils.screen_manager import ScreenManager
from shared import deeplinks
from shared.models.user import User

logger = logging.getLogger(__name__)
router = Router(name="start")


class Onboarding(StatesGroup):
    """Шаги регистрации."""
    waiting_lang = State()
    waiting_contact = State()


async def show_open_app(bot: Bot, user: User, param: str | None = None, text_key: str = "welcome") -> None:
    """Показать кнопку запуска приложения (с диплинком, если есть)."""
    screen = ScreenManager(bot)
    keyboard = open_app_keyboard(user.lang, param)
    if not keyboard:
        # Адрес Mini App не настроен — честно говорим об этом
        await screen.show(user.id, t(user.lang, "no_webapp"), slot="inline")
        return
    key = "deeplink_ready" if param else text_key
    await screen.show(user.id, t(user.lang, key), slot="inline", reply_markup=keyboard)


async def ask_contact(bot: Bot, user: User) -> None:
    """Попросить номер телефона."""
    screen = ScreenManager(bot)
    await screen.show(user.id, t(user.lang, "ask_phone"), slot="main", reply_markup=contact_keyboard(user.lang))


async def continue_onboarding(bot: Bot, state: FSMContext, user: User) -> None:
    """Следующий шаг: телефон, если его нет, иначе — кнопка приложения с диплинком."""
    if not user.phone:
        await state.set_state(Onboarding.waiting_contact)
        await ask_contact(bot, user)
        return

    data = await state.get_data()
    await state.clear()
    await show_open_app(bot, user, data.get("pending_param"))


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession, bot: Bot):
    """Команда /start — регистрация и кнопка запуска."""
    await state.clear()

    user, created = await user_service.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_premium=message.from_user.is_premium or False,
    )

    # Payload из ссылки запоминаем до конца регистрации
    param = (command.args or "").strip()
    if deeplinks.is_valid_param(param):
        await state.update_data(pending_param=param)
        logger.info("[BOT] /start с диплинком: user=%s, param=%s", user.id, param)

    # Новому пользователю — выбор языка
    if created:
        logger.info("[BOT] Новый пользователь: %s (%s)", user.full_name, user.id)
        await state.set_state(Onboarding.waiting_lang)
        await ScreenManager(bot).show(
            user.id, t(user.lang, "choose_lang"), slot="inline", reply_markup=language_keyboard(),
        )
        return

    await continue_onboarding(bot, state, user)


@router.callback_query(F.data.startswith("lang:"))
async def on_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Выбран язык — сохраняем и идём дальше."""
    lang = callback.data.split(":")[1]
    if lang not in SUPPORTED_LANGS:
        await callback.answer()
        return

    user, _ = await user_service.get_or_create_user(
        session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
    )
    await user_service.update_user(session, user, lang=lang)
    await callback.answer(t(lang, "lang_saved"))

    # Кнопки выбора больше не нужны
    await ScreenManager(bot).delete_slot(user.id, "inline")
    await continue_onboarding(bot, state, user)


@router.message(Command("lang"))
async def cmd_lang(message: Message, session: AsyncSession, bot: Bot):
    """Сменить язык бота."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    await ScreenManager(bot).show(user.id, t(user.lang, "choose_lang"), slot="inline", reply_markup=language_keyboard())


@router.message(F.contact)
async def on_contact(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Пришёл контакт — сохраняем номер. Принимаем в любом состоянии:
    Mini App тоже может запросить номер через requestContact."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    contact = message.contact

    # Пересланный чужой контакт не принимаем
    if contact.user_id != message.from_user.id:
        await message.answer(t(user.lang, "phone_not_yours"), reply_markup=contact_keyboard(user.lang))
        return

    await user_service.update_user(session, user, phone=contact.phone_number)
    logger.info("[BOT] Телефон сохранён: user=%s", user.id)

    # Убираем reply-клавиатуру и ведём в приложение
    screen = ScreenManager(bot)
    await screen.delete_slot(user.id, "main")
    await screen.show(user.id, t(user.lang, "phone_saved"), slot="temp", reply_markup=ReplyKeyboardRemove())
    await continue_onboarding(bot, state, user)


@router.message(Command("app"))
async def cmd_app(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Кнопка запуска по запросу."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    await continue_onboarding(bot, state, user)


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, bot: Bot):
    """Справка."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    await ScreenManager(bot).show(user.id, t(user.lang, "help"), slot="inline", reply_markup=open_app_keyboard(user.lang))


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession, bot: Bot):
    """Открыть админ-панель Mini App."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    if not admin_service.is_admin(user):
        await message.answer(t(user.lang, "admin_only"))
        return
    await show_open_app(bot, user, "admin")
