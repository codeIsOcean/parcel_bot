import logging
from datetime import datetime
from html import escape

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import flight_service, user_service
from bot.keyboards.city_kb import (
    get_city_keyboard, get_confirm_keyboard, get_cancel_keyboard,
)
from bot.states.flight_states import PublishFlightStates
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager

logger = logging.getLogger(__name__)
router = Router(name="publish_flight")


# === Вход в FSM: кнопка "Опубликовать рейс" ===

@router.message(F.text.contains("Опубликовать рейс") | F.text.contains("Publish flight"))
async def start_publish_flight(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Начало FSM — публикация рейса. Шаг 0: выбор города отправления."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    await state.set_state(PublishFlightStates.from_city)
    await state.update_data(lang=lang)

    await screen.show(
        message.from_user.id,
        t(lang, "choose_from_city"),
        slot="inline",
        reply_markup=get_city_keyboard(lang, prefix="flight_from"),
    )


# === Шаг 0: Город отправления ===

@router.callback_query(PublishFlightStates.from_city, F.data.startswith("flight_from:"))
async def on_flight_from_city(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбран город отправления рейса."""
    city = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    if city == "other":
        await screen.edit(callback.from_user.id, t(lang, "enter_city_name"), slot="inline")
        await state.update_data(waiting_custom_city="from")
        await callback.answer()
        return

    await state.update_data(from_city=city)
    await state.set_state(PublishFlightStates.to_city)

    await screen.edit(
        callback.from_user.id,
        t(lang, "choose_to_city"),
        slot="inline",
        reply_markup=get_city_keyboard(lang, prefix="flight_to"),
    )
    await callback.answer()


# === Шаг 1: Город назначения ===

@router.callback_query(PublishFlightStates.to_city, F.data.startswith("flight_to:"))
async def on_flight_to_city(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбран город назначения рейса."""
    city = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    if city == "other":
        await screen.edit(callback.from_user.id, t(lang, "enter_city_name"), slot="inline")
        await state.update_data(waiting_custom_city="to")
        await callback.answer()
        return

    if city == data.get("from_city"):
        await callback.answer(t(lang, "cities_differ"), show_alert=True)
        return

    await state.update_data(to_city=city)
    await state.set_state(PublishFlightStates.flight_date)

    await screen.edit(
        callback.from_user.id,
        t(lang, "enter_flight_date"),
        slot="inline",
        reply_markup=get_cancel_keyboard(lang),
    )
    await callback.answer()


# === Свободный ввод города ===

@router.message(PublishFlightStates.from_city, F.text)
@router.message(PublishFlightStates.to_city, F.text)
async def on_flight_custom_city(message: Message, state: FSMContext, bot: Bot):
    """Пользователь вводит название города для рейса."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)
    custom_target = data.get("waiting_custom_city")

    # Игнорируем текст если не ожидаем ввод города (пользователь должен выбрать из клавиатуры)
    if not custom_target:
        return

    city_name = message.text.strip()

    if not city_name or len(city_name) < 2:
        await screen.show(message.from_user.id, t(lang, "enter_city_name"), slot="temp")
        return

    if custom_target == "from":
        await state.update_data(from_city=city_name, waiting_custom_city=None)
        await state.set_state(PublishFlightStates.to_city)
        await screen.show(
            message.from_user.id,
            t(lang, "choose_to_city"),
            slot="inline",
            reply_markup=get_city_keyboard(lang, prefix="flight_to"),
        )
    else:
        await state.update_data(to_city=city_name, waiting_custom_city=None)
        await state.set_state(PublishFlightStates.flight_date)
        await screen.show(
            message.from_user.id,
            t(lang, "enter_flight_date"),
            slot="inline",
            reply_markup=get_cancel_keyboard(lang),
        )


# === Шаг 2: Дата вылета ===

@router.message(PublishFlightStates.flight_date, F.text)
async def on_flight_date(message: Message, state: FSMContext, bot: Bot):
    """Пользователь ввёл дату вылета."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    try:
        flight_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        if flight_date < datetime.now().date():
            raise ValueError("past date")
    except ValueError:
        await screen.show(message.from_user.id, t(lang, "invalid_date"), slot="temp")
        return

    await state.update_data(flight_date=flight_date.isoformat())
    await state.set_state(PublishFlightStates.available_kg)

    await screen.show(
        message.from_user.id,
        t(lang, "enter_available_kg"),
        slot="inline",
        reply_markup=get_cancel_keyboard(lang),
    )


# === Шаг 3: Свободный вес ===

@router.message(PublishFlightStates.available_kg, F.text)
async def on_available_kg(message: Message, state: FSMContext, bot: Bot):
    """Пользователь ввёл свободный вес."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    try:
        kg = float(message.text.replace(",", "."))
        if kg <= 0 or kg > 100:
            raise ValueError
    except ValueError:
        await screen.show(message.from_user.id, t(lang, "invalid_number"), slot="temp")
        return

    await state.update_data(available_kg=kg)
    await state.set_state(PublishFlightStates.price_per_kg)

    await screen.show(
        message.from_user.id,
        t(lang, "enter_price_per_kg"),
        slot="inline",
        reply_markup=get_cancel_keyboard(lang),
    )


# === Шаг 4: Цена за кг ===

@router.message(PublishFlightStates.price_per_kg, F.text)
async def on_price_per_kg(message: Message, state: FSMContext, bot: Bot):
    """Пользователь ввёл цену за кг."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    try:
        price = float(message.text.replace(",", ".").replace("$", ""))
        if price <= 0 or price > 500:
            raise ValueError
    except ValueError:
        await screen.show(message.from_user.id, t(lang, "invalid_number"), slot="temp")
        return

    await state.update_data(price_per_kg=price)
    await _show_flight_confirm(message.from_user.id, state, screen, lang)


# === Шаг 5: Подтверждение ===

async def _show_flight_confirm(chat_id: int, state: FSMContext, screen: ScreenManager, lang: str):
    """Показать экран подтверждения рейса."""
    data = await state.get_data()
    await state.set_state(PublishFlightStates.confirm)

    text = t(
        lang, "confirm_flight",
        from_city=escape(data.get("from_city", "")),
        to_city=escape(data.get("to_city", "")),
        flight_date=data.get("flight_date", ""),
        available_kg=data.get("available_kg", 0),
        price_per_kg=data.get("price_per_kg", 0),
    )
    await screen.show(chat_id, text, slot="inline", reply_markup=get_confirm_keyboard(lang))


@router.callback_query(PublishFlightStates.confirm, F.data == "confirm:yes")
async def on_confirm_flight(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Подтверждение — создаём рейс в БД."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    flight_date = datetime.fromisoformat(data["flight_date"]).date()

    try:
        await flight_service.create_flight(
            session,
            traveler_id=callback.from_user.id,
            from_city=data["from_city"],
            to_city=data["to_city"],
            flight_date=flight_date,
            available_kg=data["available_kg"],
            price_per_kg=data["price_per_kg"],
        )
    except Exception as e:
        logger.error("[PUBLISH_FLIGHT] Ошибка создания рейса: %s", e)
        await state.clear()
        await screen.show(callback.from_user.id, "❌ Error", slot="temp")
        await callback.answer()
        return

    await state.clear()

    await screen.edit(callback.from_user.id, t(lang, "flight_published"), slot="inline")
    await callback.answer(t(lang, "flight_published"), show_alert=True)


@router.callback_query(PublishFlightStates.confirm, F.data == "confirm:edit")
async def on_edit_flight(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Кнопка 'Изменить' — начать сначала."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    await state.clear()
    await state.set_state(PublishFlightStates.from_city)
    await state.update_data(lang=lang)

    await screen.edit(
        callback.from_user.id,
        t(lang, "choose_from_city"),
        slot="inline",
        reply_markup=get_city_keyboard(lang, prefix="flight_from"),
    )
    await callback.answer()
