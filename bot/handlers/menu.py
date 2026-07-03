import logging

from aiogram import Bot, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import user_service
from bot.keyboards.main_kb import get_sender_menu, get_traveler_menu, get_webapp_button
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager
from shared.models.user import UserRole

logger = logging.getLogger(__name__)
router = Router(name="menu")


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Команда /menu — показать главное меню."""
    # Очищаем FSM
    await state.clear()

    user, _ = await user_service.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Показываем меню по роли
    if user.role in (UserRole.TRAVELER, UserRole.BOTH):
        kb = get_traveler_menu(lang)
    else:
        kb = get_sender_menu(lang)

    await screen.show(message.from_user.id, t(lang, "start_welcome"), slot="main", reply_markup=kb)


@router.callback_query(F.data == "menu:main")
async def on_menu_main(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Callback — вернуться в главное меню."""
    await state.clear()

    user, _ = await user_service.get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Удаляем inline сообщение
    await screen.delete_slot(callback.from_user.id, "inline")

    # Показываем меню
    if user.role in (UserRole.TRAVELER, UserRole.BOTH):
        kb = get_traveler_menu(lang)
    else:
        kb = get_sender_menu(lang)

    await screen.show(callback.from_user.id, t(lang, "start_welcome"), slot="main", reply_markup=kb)
    await callback.answer()


@router.message(F.text.contains("Мои посылки") | F.text.contains("My parcels"), StateFilter(None))
async def on_my_parcels(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Мои посылки'."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    await _show_parcels_page(message.from_user.id, user, session, bot, page=1)


@router.callback_query(F.data.startswith("parcels_page:"))
async def on_parcels_page(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Пагинация списка посылок."""
    page = int(callback.data.split(":")[1])
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
    )
    await _show_parcels_page(callback.from_user.id, user, session, bot, page=page, edit=True)
    await callback.answer()


async def _show_parcels_page(chat_id: int, user, session: AsyncSession, bot: Bot, page: int = 1, edit: bool = False):
    """Показать страницу списка посылок с пагинацией."""
    from backend.app.services import parcel_service

    lang = user.lang
    screen = ScreenManager(bot)
    limit = 5

    try:
        parcels, total = await parcel_service.get_user_parcels(session, user.id, page=page, limit=limit)
    except Exception as e:
        logger.error("[MENU] Ошибка загрузки посылок: %s", e)
        await screen.show(chat_id, "❌ Error", slot="temp")
        return

    if not parcels:
        await screen.show(chat_id, t(lang, "no_parcels"), slot="inline")
        return

    # Формируем текст со списком посылок
    total_pages = (total + limit - 1) // limit
    lines = [f"📋 <b>{t(lang, 'my_parcels')}</b> ({page}/{total_pages}, {t(lang, 'total')}: {total})\n"]
    for p in parcels:
        status_emoji = {"pending": "⏳", "accepted": "✅", "handed": "🤝",
                        "in_transit": "✈️", "delivered": "📦", "cancelled": "❌"}
        emoji = status_emoji.get(p.status.value, "❓")
        lines.append(f"{emoji} {p.from_city} → {p.to_city} | {p.weight}кг | ${p.price}")

    # Кнопки пагинации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"parcels_page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"parcels_page:{page + 1}"))

    kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons]) if nav_buttons else None

    if edit:
        await screen.edit(chat_id, "\n".join(lines), slot="inline", reply_markup=kb)
    else:
        await screen.show(chat_id, "\n".join(lines), slot="inline", reply_markup=kb)


@router.message(F.text.contains("Мои рейсы") | F.text.contains("My flights"), StateFilter(None))
async def on_my_flights(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Мои рейсы'."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    await _show_flights_page(message.from_user.id, user, session, bot, page=1)


@router.callback_query(F.data.startswith("flights_page:"))
async def on_flights_page(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    """Пагинация списка рейсов."""
    page = int(callback.data.split(":")[1])
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
    )
    await _show_flights_page(callback.from_user.id, user, session, bot, page=page, edit=True)
    await callback.answer()


async def _show_flights_page(chat_id: int, user, session: AsyncSession, bot: Bot, page: int = 1, edit: bool = False):
    """Показать страницу списка рейсов с пагинацией."""
    from backend.app.services import flight_service

    lang = user.lang
    screen = ScreenManager(bot)
    limit = 5

    try:
        flights, total = await flight_service.get_user_flights(session, user.id, page=page, limit=limit)
    except Exception as e:
        logger.error("[MENU] Ошибка загрузки рейсов: %s", e)
        await screen.show(chat_id, "❌ Error", slot="temp")
        return

    if not flights:
        await screen.show(chat_id, t(lang, "no_flights"), slot="inline")
        return

    # Формируем текст со списком рейсов
    total_pages = (total + limit - 1) // limit
    lines = [f"📋 <b>{t(lang, 'my_flights')}</b> ({page}/{total_pages}, {t(lang, 'total')}: {total})\n"]
    for f in flights:
        lines.append(
            f"✈️ {f.from_city} → {f.to_city} | {f.flight_date} | "
            f"{f.available_kg}кг | ${f.price_per_kg}/кг"
        )

    # Кнопки пагинации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"flights_page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"flights_page:{page + 1}"))

    kb = InlineKeyboardMarkup(inline_keyboard=[nav_buttons]) if nav_buttons else None

    if edit:
        await screen.edit(chat_id, "\n".join(lines), slot="inline", reply_markup=kb)
    else:
        await screen.show(chat_id, "\n".join(lines), slot="inline", reply_markup=kb)


@router.message(F.text.contains("Найти попутчика") | F.text.contains("Find traveler"), StateFilter(None))
async def on_find_travelers(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Найти попутчика' — направляем в webapp."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Показываем кнопку webapp для поиска попутчиков
    webapp_kb = get_webapp_button(lang)
    await screen.show(
        message.from_user.id,
        t(lang, "open_webapp"),
        slot="inline",
        reply_markup=webapp_kb,
    )


@router.message(F.text.contains("Чаты") | F.text.contains("Chats"), StateFilter(None))
async def on_chats(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Чаты' — пока нет активных чатов."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    await screen.show(message.from_user.id, t(lang, "no_chats"), slot="inline")


@router.message(F.text.contains("Входящие заявки") | F.text.contains("Incoming requests"), StateFilter(None))
async def on_incoming_requests(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Входящие заявки' — направляем в webapp."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Показываем кнопку webapp для входящих заявок
    webapp_kb = get_webapp_button(lang)
    await screen.show(
        message.from_user.id,
        t(lang, "open_webapp"),
        slot="inline",
        reply_markup=webapp_kb,
    )


@router.message(F.text.contains("Подписка") | F.text.contains("Subscription"), StateFilter(None))
async def on_subscription(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Подписка' — направляем в webapp."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Показываем кнопку webapp для подписки
    webapp_kb = get_webapp_button(lang)
    await screen.show(
        message.from_user.id,
        t(lang, "open_webapp"),
        slot="inline",
        reply_markup=webapp_kb,
    )
