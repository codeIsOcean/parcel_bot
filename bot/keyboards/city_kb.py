from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.locale import t


# Список городов с callback_data
CITIES = [
    ("Dubai", "🇦🇪"),
    ("Almaty", "🇰🇿"),
    ("Moscow", "🇷🇺"),
    ("Istanbul", "🇹🇷"),
    ("Astana", "🇰🇿"),
    ("New York", "🇺🇸"),
]


def get_city_keyboard(lang: str = "ru", prefix: str = "city_from") -> InlineKeyboardMarkup:
    """Клавиатура выбора города."""
    buttons = []

    # Города по 2 в строке
    row = []
    for city_name, flag in CITIES:
        # Локализованное название
        city_key = f"city_{city_name.lower().replace(' ', '')}"
        localized = t(lang, city_key) if t(lang, city_key) != city_key else city_name

        row.append(InlineKeyboardButton(
            text=f"{flag} {localized}",
            callback_data=f"{prefix}:{city_name}",
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Кнопка "Другой город"
    buttons.append([
        InlineKeyboardButton(text=t(lang, "other_city"), callback_data=f"{prefix}:other"),
    ])

    # Кнопки навигации
    buttons.append([
        InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_weight_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора веса (кг)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 кг", callback_data="weight:1"),
            InlineKeyboardButton(text="2 кг", callback_data="weight:2"),
            InlineKeyboardButton(text="3 кг", callback_data="weight:3"),
        ],
        [
            InlineKeyboardButton(text="5 кг", callback_data="weight:5"),
            InlineKeyboardButton(text="10 кг", callback_data="weight:10"),
            InlineKeyboardButton(text=t(lang, "other_weight"), callback_data="weight:other"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "back"), callback_data="back:weight"),
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])


def get_price_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора цены ($)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="$15", callback_data="price:15"),
            InlineKeyboardButton(text="$20", callback_data="price:20"),
            InlineKeyboardButton(text="$30", callback_data="price:30"),
        ],
        [
            InlineKeyboardButton(text="$50", callback_data="price:50"),
            InlineKeyboardButton(text=t(lang, "other_price"), callback_data="price:other"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "back"), callback_data="back:price"),
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])


def get_confirm_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения (Подтвердить / Изменить / Отмена)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "confirm"), callback_data="confirm:yes"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "edit"), callback_data="confirm:edit"),
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])


def get_photo_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура для шага с фото (Пропустить / Назад / Отмена)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "skip"), callback_data="photo:skip"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "back"), callback_data="back:photo"),
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])


def get_cancel_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура с единственной кнопкой 'Отмена' — для текстовых шагов FSM."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])
