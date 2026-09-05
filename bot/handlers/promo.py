"""Работа бота в групповых чатах.

Две задачи. Первая — администратор подключает чат к рассылке рейсов.
Вторая — бот замечает в группе объявление вида «везу Дубай — Алматы»
и предлагает автору оформить рейс в приложении. Так объявления из чатов
затягиваются внутрь сервиса, где есть рейтинг и статусы доставки.
"""

import logging
import time

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services import crosspost_service
from shared.locale.notify_texts import nt
from shared.models.city import City

logger = logging.getLogger(__name__)
router = Router(name="promo")

# Роутер работает только в группах — приватные чаты обслуживают другие роутеры
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Слова, по которым узнаём объявление перевозчика
CARRIER_KEYWORDS = (
    "везу", "повезу", "вожу", "лечу", "полечу", "беру посылк", "возьму посылк",
    "свободн", "багаж",
    "carry", "flying", "flight", "luggage", "kg free",
)

# Как часто можно предлагать одному человеку в одном чате (сутки)
OFFER_COOLDOWN_SECONDS = 24 * 60 * 60

# Кеш названий городов, чтобы не ходить в базу на каждое сообщение группы
_cities_cache: set[str] = set()
_cities_cached_at: float = 0.0
_CITIES_TTL_SECONDS = 600

# Когда последний раз предлагали: (chat_id, user_id) → время
_last_offer: dict[tuple[int, int], float] = {}


async def _get_city_names(session: AsyncSession) -> set[str]:
    """Названия городов в нижнем регистре, с кешем на несколько минут."""
    global _cities_cache, _cities_cached_at

    now = time.time()
    if _cities_cache and now - _cities_cached_at < _CITIES_TTL_SECONDS:
        return _cities_cache

    rows = (await session.execute(select(City))).scalars().all()
    names = set()
    for city in rows:
        for value in (city.name_ru, city.name_en, city.name_kz):
            if value:
                names.add(value.lower())

    _cities_cache = names
    _cities_cached_at = now
    return names


def _is_carrier_message(text: str) -> bool:
    """Похоже ли сообщение на объявление перевозчика."""
    lowered = text.lower().replace("ё", "е")
    return any(word in lowered for word in CARRIER_KEYWORDS)


def _found_cities(text: str, city_names: set[str]) -> list[str]:
    """Города, упомянутые в сообщении."""
    lowered = text.lower()
    # Длинные названия проверяем первыми, чтобы «нью-йорк» не съел «йорк»
    found = [name for name in sorted(city_names, key=len, reverse=True) if name in lowered]

    # Убираем названия, которые являются частью уже найденного
    result: list[str] = []
    for name in found:
        if not any(name != other and name in other for other in result):
            result.append(name)
    return result


def _on_cooldown(chat_id: int, user_id: int) -> bool:
    """Не предлагали ли мы этому человеку недавно."""
    last = _last_offer.get((chat_id, user_id))
    return bool(last and time.time() - last < OFFER_COOLDOWN_SECONDS)


def _publish_markup(lang: str = "ru") -> InlineKeyboardMarkup | None:
    """Кнопка «Оформить рейс», ведущая в приложение."""
    # В группах кнопка web_app не работает, поэтому ссылка на бота
    if not settings.bot_username:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=nt(lang, "btn_publish_flight"),
            url=f"https://t.me/{settings.bot_username}?startapp=publish",
        ),
    ]])


def _is_admin(user_id: int) -> bool:
    """Разрешено ли пользователю управлять рассылкой."""
    return user_id in settings.admin_id_list


@router.message(Command("promo_add"))
async def cmd_promo_add(message: Message, session: AsyncSession):
    """Подключить текущий чат к рассылке рейсов."""
    if not _is_admin(message.from_user.id):
        await message.reply(nt("ru", "promo_admin_only"))
        return

    await crosspost_service.add_chat(
        session,
        chat_id=message.chat.id,
        title=message.chat.title,
        added_by=message.from_user.id,
    )
    await message.reply(nt("ru", "promo_chat_added"))


@router.message(Command("promo_off"))
async def cmd_promo_off(message: Message, session: AsyncSession):
    """Отключить текущий чат от рассылки рейсов."""
    if not _is_admin(message.from_user.id):
        await message.reply(nt("ru", "promo_admin_only"))
        return

    await crosspost_service.remove_chat(session, message.chat.id)
    await message.reply(nt("ru", "promo_chat_removed"))


@router.message(F.text)
async def on_group_message(message: Message, session: AsyncSession, bot: Bot):
    """Заметить объявление перевозчика и предложить оформить рейс."""
    text = message.text or ""

    # Слишком короткое сообщение объявлением быть не может
    if len(text) < 12 or not _is_carrier_message(text):
        return

    # Нужны хотя бы два города — маршрут
    cities = _found_cities(text, await _get_city_names(session))
    if len(cities) < 2:
        return

    # Не надоедаем: одному человеку в одном чате не чаще раза в сутки
    if _on_cooldown(message.chat.id, message.from_user.id):
        return
    _last_offer[(message.chat.id, message.from_user.id)] = time.time()

    route = f"{cities[0].title()} → {cities[1].title()}"
    logger.info(
        "[PROMO] Объявление в чате %s: user=%s, маршрут=%s",
        message.chat.id, message.from_user.id, route,
    )

    try:
        await message.reply(nt("ru", "group_offer", route=route), reply_markup=_publish_markup())
    except Exception as e:
        # В группе бота могут ограничить в правах — это не повод падать
        logger.warning("[PROMO] Не удалось ответить в чате %s: %s", message.chat.id, e)
