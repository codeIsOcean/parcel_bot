import logging
from html import escape

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import parcel_service, user_service
from bot.keyboards.city_kb import (
    get_city_keyboard, get_weight_keyboard,
    get_price_keyboard, get_confirm_keyboard, get_photo_keyboard,
    get_cancel_keyboard,
)
from bot.states.parcel_states import CreateParcelStates
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager

logger = logging.getLogger(__name__)
router = Router(name="create_parcel")


# === Вход в FSM: кнопка "Отправить посылку" ===

@router.message(F.text.contains("Отправить посылку") | F.text.contains("Send parcel"))
async def start_create_parcel(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Начало FSM — создание посылки. Шаг 0: выбор города отправления."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Устанавливаем FSM состояние
    await state.set_state(CreateParcelStates.from_city)
    await state.update_data(lang=lang)

    # Показываем клавиатуру городов
    await screen.show(
        message.from_user.id,
        t(lang, "choose_from_city"),
        slot="inline",
        reply_markup=get_city_keyboard(lang, prefix="city_from"),
    )


# === Шаг 0: Город отправления ===

@router.callback_query(CreateParcelStates.from_city, F.data.startswith("city_from:"))
async def on_from_city(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбран город отправления."""
    city = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    if city == "other":
        # Свободный ввод города
        await screen.edit(callback.from_user.id, t(lang, "enter_city_name"), slot="inline")
        await state.update_data(waiting_custom_city="from")
        await callback.answer()
        return

    # Сохраняем город и переходим к шагу 1
    await state.update_data(from_city=city)
    await state.set_state(CreateParcelStates.to_city)

    await screen.edit(
        callback.from_user.id,
        t(lang, "choose_to_city"),
        slot="inline",
        reply_markup=get_city_keyboard(lang, prefix="city_to"),
    )
    await callback.answer()


# === Шаг 1: Город назначения ===

@router.callback_query(CreateParcelStates.to_city, F.data.startswith("city_to:"))
async def on_to_city(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбран город назначения."""
    city = callback.data.split(":", 1)[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    if city == "other":
        await screen.edit(callback.from_user.id, t(lang, "enter_city_name"), slot="inline")
        await state.update_data(waiting_custom_city="to")
        await callback.answer()
        return

    # Проверяем что город отличается от города отправления
    if city == data.get("from_city"):
        await callback.answer(t(lang, "cities_differ"), show_alert=True)
        return

    # Сохраняем и переходим к шагу 2 (описание)
    await state.update_data(to_city=city)
    await state.set_state(CreateParcelStates.description)

    await screen.edit(
        callback.from_user.id,
        t(lang, "enter_description"),
        slot="inline",
        reply_markup=get_cancel_keyboard(lang),
    )
    await callback.answer()


# === Свободный ввод города (для "Другой город") ===

@router.message(CreateParcelStates.from_city, F.text)
@router.message(CreateParcelStates.to_city, F.text)
async def on_custom_city_input(message: Message, state: FSMContext, bot: Bot):
    """Пользователь вводит название своего города."""
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
        await state.set_state(CreateParcelStates.to_city)
        await screen.show(
            message.from_user.id,
            t(lang, "choose_to_city"),
            slot="inline",
            reply_markup=get_city_keyboard(lang, prefix="city_to"),
        )
    else:
        await state.update_data(to_city=city_name, waiting_custom_city=None)
        await state.set_state(CreateParcelStates.description)
        await screen.show(
            message.from_user.id,
            t(lang, "enter_description"),
            slot="inline",
            reply_markup=get_cancel_keyboard(lang),
        )


# === Шаг 2: Описание ===

@router.message(CreateParcelStates.description, F.text)
async def on_description(message: Message, state: FSMContext, bot: Bot):
    """Пользователь ввёл описание посылки."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    description = message.text.strip()
    if len(description) < 3:
        await screen.show(message.from_user.id, t(lang, "enter_description"), slot="temp")
        return

    await state.update_data(description=description)
    await state.set_state(CreateParcelStates.weight)

    await screen.show(
        message.from_user.id,
        t(lang, "choose_weight"),
        slot="inline",
        reply_markup=get_weight_keyboard(lang),
    )


# === Шаг 3: Вес ===

@router.callback_query(CreateParcelStates.weight, F.data.startswith("weight:"))
async def on_weight_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбран вес посылки."""
    value = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    if value == "other":
        # Просим пользователя ввести вес вручную
        await screen.edit(callback.from_user.id, t(lang, "enter_weight_manual"), slot="inline")
        await callback.answer()
        return

    await state.update_data(weight=float(value))
    await state.set_state(CreateParcelStates.photo)

    await screen.edit(
        callback.from_user.id,
        t(lang, "send_photo"),
        slot="inline",
        reply_markup=get_photo_keyboard(lang),
    )
    await callback.answer()


@router.message(CreateParcelStates.weight, F.text)
async def on_weight_manual(message: Message, state: FSMContext, bot: Bot):
    """Ручной ввод веса."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    try:
        weight = float(message.text.replace(",", "."))
        if weight <= 0 or weight > 50:
            raise ValueError
    except ValueError:
        await screen.show(message.from_user.id, t(lang, "invalid_number"), slot="temp")
        return

    await state.update_data(weight=weight)
    await state.set_state(CreateParcelStates.photo)

    await screen.show(
        message.from_user.id,
        t(lang, "send_photo"),
        slot="inline",
        reply_markup=get_photo_keyboard(lang),
    )


# === Шаг 4: Фото ===

@router.callback_query(CreateParcelStates.photo, F.data == "photo:skip")
async def on_photo_skip(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Пропуск фото."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    await state.set_state(CreateParcelStates.price)

    await screen.edit(
        callback.from_user.id,
        t(lang, "choose_price"),
        slot="inline",
        reply_markup=get_price_keyboard(lang),
    )
    await callback.answer()


@router.message(CreateParcelStates.photo, F.photo)
async def on_photo_received(message: Message, state: FSMContext, bot: Bot):
    """Получено фото посылки."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    # Сохраняем file_id самого большого размера
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    await state.set_state(CreateParcelStates.price)

    await screen.show(
        message.from_user.id,
        t(lang, "choose_price"),
        slot="inline",
        reply_markup=get_price_keyboard(lang),
    )


# === Шаг 5: Цена ===

@router.callback_query(CreateParcelStates.price, F.data.startswith("price:"))
async def on_price_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбрана цена."""
    value = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    if value == "other":
        # Просим пользователя ввести цену вручную
        await screen.edit(callback.from_user.id, t(lang, "enter_price_manual"), slot="inline")
        await callback.answer()
        return

    await state.update_data(price=float(value))
    await _show_confirm(callback.from_user.id, state, screen, lang)
    await callback.answer()


@router.message(CreateParcelStates.price, F.text)
async def on_price_manual(message: Message, state: FSMContext, bot: Bot):
    """Ручной ввод цены."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    try:
        price = float(message.text.replace(",", ".").replace("$", ""))
        if price <= 0 or price > 10000:
            raise ValueError
    except ValueError:
        await screen.show(message.from_user.id, t(lang, "invalid_number"), slot="temp")
        return

    await state.update_data(price=price)
    await _show_confirm(message.from_user.id, state, screen, lang)


# === Шаг 6: Подтверждение ===

async def _show_confirm(chat_id: int, state: FSMContext, screen: ScreenManager, lang: str):
    """Показать экран подтверждения."""
    data = await state.get_data()
    await state.set_state(CreateParcelStates.confirm)

    text = t(
        lang, "confirm_parcel",
        from_city=escape(data.get("from_city", "")),
        to_city=escape(data.get("to_city", "")),
        description=escape(data.get("description", "")),
        weight=data.get("weight", 0),
        price=data.get("price", 0),
    )
    await screen.show(chat_id, text, slot="inline", reply_markup=get_confirm_keyboard(lang))


@router.callback_query(CreateParcelStates.confirm, F.data == "confirm:yes")
async def on_confirm_parcel(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Подтверждение — создаём посылку в БД."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    # Создаём посылку через сервис
    try:
        parcel = await parcel_service.create_parcel(
            session,
            sender_id=callback.from_user.id,
            from_city=data["from_city"],
            to_city=data["to_city"],
            description=data["description"],
            weight=data["weight"],
            size="medium",
            price=data["price"],
        )

        # Если есть фото — обновляем
        if data.get("photo_file_id"):
            parcel.photo_file_ids = data["photo_file_id"]
            await session.commit()
    except Exception as e:
        logger.error("[CREATE_PARCEL] Ошибка создания посылки: %s", e)
        await state.clear()
        await screen.show(callback.from_user.id, "❌ Error", slot="temp")
        await callback.answer()
        return

    # Очищаем FSM
    await state.clear()

    # Показываем успех
    await screen.edit(callback.from_user.id, t(lang, "parcel_created"), slot="inline")
    await callback.answer(t(lang, "parcel_created"), show_alert=True)


@router.callback_query(CreateParcelStates.confirm, F.data == "confirm:edit")
async def on_edit_parcel(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Кнопка 'Изменить' — начать сначала."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    # Возвращаемся к первому шагу, сохраняя lang
    await state.clear()
    await state.set_state(CreateParcelStates.from_city)
    await state.update_data(lang=lang)

    await screen.edit(
        callback.from_user.id,
        t(lang, "choose_from_city"),
        slot="inline",
        reply_markup=get_city_keyboard(lang, prefix="city_from"),
    )
    await callback.answer()


# === Кнопки "Назад" ===

@router.callback_query(CreateParcelStates.weight, F.data == "back:weight")
async def on_back_to_description(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Назад из шага веса → шаг описания."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    await state.set_state(CreateParcelStates.description)
    await screen.edit(callback.from_user.id, t(lang, "enter_description"), slot="inline",
                      reply_markup=get_cancel_keyboard(lang))
    await callback.answer()


@router.callback_query(CreateParcelStates.photo, F.data == "back:photo")
async def on_back_to_weight(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Назад из шага фото → шаг веса."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    await state.set_state(CreateParcelStates.weight)
    await screen.edit(
        callback.from_user.id,
        t(lang, "choose_weight"),
        slot="inline",
        reply_markup=get_weight_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(CreateParcelStates.price, F.data == "back:price")
async def on_back_to_photo(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Назад из шага цены → шаг фото."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    await state.set_state(CreateParcelStates.photo)
    await screen.edit(
        callback.from_user.id,
        t(lang, "send_photo"),
        slot="inline",
        reply_markup=get_photo_keyboard(lang),
    )
    await callback.answer()


