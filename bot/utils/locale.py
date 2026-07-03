import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Загружаем локали из shared/locale (общие с webapp)
_locales = {}
_locale_dir = Path(__file__).parent.parent.parent / "webapp" / "src" / "locale"

# Дополнительные строки только для бота
_bot_strings = {
    "ru": {
        "start_welcome": "👋 Добро пожаловать в <b>Parcel Bot</b>!\n\nСервис доставки посылок через попутчиков на международных рейсах.",
        "choose_role": "Выберите свою роль:",
        "role_sender_desc": "📦 <b>Отправитель</b>\nОтправить посылку с попутчиком",
        "role_traveler_desc": "✈️ <b>Перевозчик</b>\nЗаработать на свободном месте в багаже",
        "menu_sender": "📦 Отправить посылку\n🔍 Найти попутчика\n📋 Мои посылки\n💬 Мои чаты\n👤 Профиль\n⚙️ Настройки",
        "menu_traveler": "✈️ Опубликовать рейс\n📋 Мои рейсы\n📩 Входящие заявки\n💬 Мои чаты\n👤 Профиль\n⭐ Подписка",
        "choose_from_city": "🟢 Выберите город <b>отправления</b>:",
        "choose_to_city": "🔴 Выберите город <b>назначения</b>:",
        "enter_description": "📝 Опишите содержимое посылки:",
        "choose_weight": "⚖️ Выберите <b>вес</b> посылки (кг):",
        "send_photo": "📷 Отправьте <b>фото</b> посылки или нажмите <b>Пропустить</b>:",
        "choose_price": "💰 Предложите <b>цену</b> за доставку ($):\n\n<i>Средняя цена: $8–12/кг</i>",
        "confirm_parcel": "📦 <b>Проверьте данные посылки:</b>\n\n"
                          "🟢 Откуда: <b>{from_city}</b>\n"
                          "🔴 Куда: <b>{to_city}</b>\n"
                          "📝 Описание: {description}\n"
                          "⚖️ Вес: <b>{weight} кг</b>\n"
                          "💰 Цена: <b>${price}</b>",
        "parcel_created": "✅ Посылка создана! Ожидайте отклик попутчиков.",
        "parcel_cancelled": "❌ Создание посылки отменено.",
        "enter_flight_date": "📅 Введите <b>дату вылета</b> (ДД.ММ.ГГГГ):",
        "enter_available_kg": "⚖️ Сколько <b>свободных кг</b> в багаже?",
        "enter_price_per_kg": "💰 Цена за <b>1 кг</b> ($):",
        "confirm_flight": "✈️ <b>Проверьте данные рейса:</b>\n\n"
                          "🟢 Откуда: <b>{from_city}</b>\n"
                          "🔴 Куда: <b>{to_city}</b>\n"
                          "📅 Дата: <b>{flight_date}</b>\n"
                          "⚖️ Свободно: <b>{available_kg} кг</b>\n"
                          "💰 Цена: <b>${price_per_kg}/кг</b>",
        "flight_published": "✅ Рейс опубликован! Ожидайте заявки.",
        "flight_cancelled": "❌ Публикация рейса отменена.",
        "no_parcels": "📦 У вас пока нет посылок.",
        "no_flights": "✈️ У вас пока нет рейсов.",
        "no_chats": "💬 Нет активных чатов.",
        "invalid_date": "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ",
        "invalid_number": "❌ Введите число.",
        "other_city": "🌍 Другой город",
        "enter_city_name": "Введите название города:",
        "skip": "Пропустить",
        "back": "🔙 Назад",
        "cancel": "❌ Отмена",
        "confirm": "✅ Подтвердить",
        "edit": "✏️ Изменить",
        "open_webapp": "🌐 Открыть приложение",
        "role_sender": "Отправитель",
        "role_traveler": "Перевозчик",
        "send_parcel": "Отправить посылку",
        "find_travelers": "Найти попутчика",
        "my_parcels": "Мои посылки",
        "chat_title": "Чаты",
        "profile_title": "Профиль",
        "publish_flight": "Опубликовать рейс",
        "incoming_requests": "Входящие заявки",
        "my_flights": "Мои рейсы",
        "subscription": "Подписка",
        "other_weight": "Другой вес",
        "other_price": "Другая цена",
        "cities_differ": "Города должны отличаться!",
        "unknown_command": "Не понял команду. Используйте меню или /menu",
        "enter_weight_manual": "Введите вес вручную (кг):",
        "enter_price_manual": "Введите цену вручную ($):",
        "settings_title": "Настройки",
        "language_changed": "✅ Язык изменён на {lang}",
        "profile_text": "👤 <b>{name}</b>\n\n"
                        "⭐ Рейтинг: {rating}\n"
                        "📦 Доставки: {deliveries}\n"
                        "💬 Отзывы: {reviews}\n"
                        "{verified_text}",
        "verified": "✅ Верифицирован",
        "not_verified": "❌ Не верифицирован",
        "total": "всего",
        "choose_rating": "⭐ Оцените доставку (1-5):",
        "enter_review_comment": "💬 Напишите комментарий или нажмите <b>Пропустить</b>:",
        "review_saved": "✅ Отзыв сохранён! Спасибо.",
    },
    "en": {
        "start_welcome": "👋 Welcome to <b>Parcel Bot</b>!\n\nDelivery service via travel companions on international flights.",
        "choose_role": "Choose your role:",
        "role_sender_desc": "📦 <b>Sender</b>\nSend a parcel with a traveler",
        "role_traveler_desc": "✈️ <b>Traveler</b>\nEarn on free luggage space",
        "menu_sender": "📦 Send parcel\n🔍 Find traveler\n📋 My parcels\n💬 My chats\n👤 Profile\n⚙️ Settings",
        "menu_traveler": "✈️ Publish flight\n📋 My flights\n📩 Incoming requests\n💬 My chats\n👤 Profile\n⭐ Subscription",
        "choose_from_city": "🟢 Select <b>departure</b> city:",
        "choose_to_city": "🔴 Select <b>destination</b> city:",
        "enter_description": "📝 Describe the parcel contents:",
        "choose_weight": "⚖️ Select parcel <b>weight</b> (kg):",
        "send_photo": "📷 Send a <b>photo</b> of the parcel or press <b>Skip</b>:",
        "choose_price": "💰 Offer a <b>price</b> for delivery ($):\n\n<i>Average price: $8–12/kg</i>",
        "confirm_parcel": "📦 <b>Review your parcel:</b>\n\n"
                          "🟢 From: <b>{from_city}</b>\n"
                          "🔴 To: <b>{to_city}</b>\n"
                          "📝 Description: {description}\n"
                          "⚖️ Weight: <b>{weight} kg</b>\n"
                          "💰 Price: <b>${price}</b>",
        "parcel_created": "✅ Parcel created! Waiting for travelers.",
        "parcel_cancelled": "❌ Parcel creation cancelled.",
        "enter_flight_date": "📅 Enter <b>flight date</b> (DD.MM.YYYY):",
        "enter_available_kg": "⚖️ How many <b>free kg</b> in your luggage?",
        "enter_price_per_kg": "💰 Price per <b>1 kg</b> ($):",
        "confirm_flight": "✈️ <b>Review your flight:</b>\n\n"
                          "🟢 From: <b>{from_city}</b>\n"
                          "🔴 To: <b>{to_city}</b>\n"
                          "📅 Date: <b>{flight_date}</b>\n"
                          "⚖️ Available: <b>{available_kg} kg</b>\n"
                          "💰 Price: <b>${price_per_kg}/kg</b>",
        "flight_published": "✅ Flight published! Waiting for requests.",
        "flight_cancelled": "❌ Flight publication cancelled.",
        "no_parcels": "📦 You have no parcels yet.",
        "no_flights": "✈️ You have no flights yet.",
        "no_chats": "💬 No active chats.",
        "invalid_date": "❌ Invalid date format. Use DD.MM.YYYY",
        "invalid_number": "❌ Enter a number.",
        "other_city": "🌍 Other city",
        "enter_city_name": "Enter city name:",
        "skip": "Skip",
        "back": "🔙 Back",
        "cancel": "❌ Cancel",
        "confirm": "✅ Confirm",
        "edit": "✏️ Edit",
        "open_webapp": "🌐 Open app",
        "role_sender": "Sender",
        "role_traveler": "Traveler",
        "send_parcel": "Send parcel",
        "find_travelers": "Find traveler",
        "my_parcels": "My parcels",
        "chat_title": "Chats",
        "profile_title": "Profile",
        "publish_flight": "Publish flight",
        "incoming_requests": "Incoming requests",
        "my_flights": "My flights",
        "subscription": "Subscription",
        "other_weight": "Other weight",
        "other_price": "Other price",
        "cities_differ": "Cities must be different!",
        "unknown_command": "Unknown command. Use the menu or /menu",
        "enter_weight_manual": "Enter weight manually (kg):",
        "enter_price_manual": "Enter price manually ($):",
        "settings_title": "Settings",
        "language_changed": "✅ Language changed to {lang}",
        "profile_text": "👤 <b>{name}</b>\n\n"
                        "⭐ Rating: {rating}\n"
                        "📦 Deliveries: {deliveries}\n"
                        "💬 Reviews: {reviews}\n"
                        "{verified_text}",
        "verified": "✅ Verified",
        "not_verified": "❌ Not verified",
        "total": "total",
        "choose_rating": "⭐ Rate the delivery (1-5):",
        "enter_review_comment": "💬 Write a comment or press <b>Skip</b>:",
        "review_saved": "✅ Review saved! Thank you.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """
    Получить локализованную строку.
    Приоритет: bot_strings → webapp locale → ключ.
    """
    # Сначала ищем в строках бота
    text = _bot_strings.get(lang, _bot_strings["ru"]).get(key)

    # Если не нашли — ищем в webapp locale
    if text is None:
        if not _locales:
            _load_webapp_locales()
        text = _locales.get(lang, _locales.get("ru", {})).get(key, key)

    # Подставляем параметры
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass

    return text


def _load_webapp_locales():
    """Загрузить JSON-локали из webapp."""
    for lang_file in _locale_dir.glob("*.json"):
        lang_code = lang_file.stem
        try:
            with open(lang_file, encoding="utf-8") as f:
                _locales[lang_code] = json.load(f)
        except Exception as e:
            logger.warning("[LOCALE] Ошибка загрузки %s: %s", lang_file, e)
