"""Клавиатуры тонкого бота: язык, телефон и одна кнопка «Открыть приложение».

Кнопка запуска — inline web_app, а не reply: reply-кнопка web_app в
Telegram Desktop открывает пустое окно «нет связи с Telegram».
"""

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    ReplyKeyboardMarkup, WebAppInfo,
)

from bot.config import WEBAPP_URL
from bot.utils.locale import t
from shared import deeplinks


def language_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка при первом запуске и по /lang."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    ]])


def contact_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Reply-кнопка запроса номера — единственный способ получить телефон из Telegram."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "btn_share_phone"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def open_app_keyboard(lang: str, param: str | None = None) -> InlineKeyboardMarkup | None:
    """Кнопка, открывающая Mini App на нужном экране. None, если адрес не настроен."""
    url = deeplinks.webapp_url(WEBAPP_URL, param)
    if not url:
        return None

    # Подпись зависит от того, куда ведём
    key = "btn_open_app"
    if param and param.startswith("parcel_"):
        key = "btn_open_parcel"
    elif param and param.startswith("flight_"):
        key = "btn_open_flight"
    elif param and param.startswith("admin"):
        key = "btn_open_admin"

    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, key), web_app=WebAppInfo(url=url)),
    ]])
