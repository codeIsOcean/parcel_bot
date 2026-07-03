from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from bot.utils.locale import t
from bot.config import WEBAPP_URL


def get_role_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура выбора роли (при /start)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 " + t(lang, "role_sender"), callback_data="role:sender"),
            InlineKeyboardButton(text="✈️ " + t(lang, "role_traveler"), callback_data="role:traveler"),
        ],
    ])


def get_sender_menu(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Reply-клавиатура главного меню отправителя."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📦 " + t(lang, "send_parcel")),
                KeyboardButton(text="🔍 " + t(lang, "find_travelers")),
            ],
            [
                KeyboardButton(text="📋 " + t(lang, "my_parcels")),
                KeyboardButton(text="💬 " + t(lang, "chat_title")),
            ],
            [
                KeyboardButton(text="👤 " + t(lang, "profile_title")),
                KeyboardButton(text="⚙️ " + t(lang, "settings_title")),
            ],
        ],
        resize_keyboard=True,
    )


def get_traveler_menu(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Reply-клавиатура главного меню перевозчика."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✈️ " + t(lang, "publish_flight")),
                KeyboardButton(text="📩 " + t(lang, "incoming_requests")),
            ],
            [
                KeyboardButton(text="📋 " + t(lang, "my_flights")),
                KeyboardButton(text="💬 " + t(lang, "chat_title")),
            ],
            [
                KeyboardButton(text="👤 " + t(lang, "profile_title")),
                KeyboardButton(text="⭐ " + t(lang, "subscription")),
            ],
        ],
        resize_keyboard=True,
    )


def get_webapp_button(lang: str = "ru") -> InlineKeyboardMarkup | None:
    """Кнопка для открытия WebApp (если URL настроен)."""
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, "open_webapp"),
            web_app=WebAppInfo(url=WEBAPP_URL),
        )],
    ])


def get_settings_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:main"),
        ],
    ])
