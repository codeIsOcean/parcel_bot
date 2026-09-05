"""Кросс-постинг рейсов в телеграм-группы.

Решает холодный старт. Перевозчику невыгодно постить в пустое приложение,
поэтому приложение само разносит его объявление по профильным чатам:
один раз заполнил карточку — объявление ушло всюду, а заявки вернулись
внутрь сервиса, где есть рейтинг, статусы и история.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from shared.locale.notify_texts import nt
from shared.models.flight import Flight
from shared.models.promo_chat import PromoChat
from shared.models.user import User
from shared.notify import fire_and_forget, send_message

logger = logging.getLogger(__name__)


def _deep_link(start_param: str) -> str | None:
    """Ссылка, открывающая Mini App с параметром запуска."""
    # В группах кнопка web_app недоступна, поэтому ведём через ссылку на бота
    if not settings.bot_username:
        return None
    return f"https://t.me/{settings.bot_username}?startapp={start_param}"


def _announcement_markup(flight_id: int, lang: str = "ru") -> dict | None:
    """Кнопка под объявлением, ведущая в приложение на нужный рейс."""
    url = _deep_link(f"flight_{flight_id}")
    if not url:
        return None
    return {
        "inline_keyboard": [[
            {"text": nt(lang, "btn_send_with_him"), "url": url},
        ]]
    }


async def get_target_chats(session: AsyncSession, flight: Flight) -> list[PromoChat]:
    """Активные чаты, которым подходит маршрут этого рейса."""
    chats = list((await session.execute(
        select(PromoChat).where(PromoChat.is_active == True)  # noqa: E712
    )).scalars().all())

    # Фильтр по городам задаётся на самом чате
    return [c for c in chats if c.matches_route(flight.from_city, flight.to_city)]


async def announce_flight(session: AsyncSession, flight: Flight) -> int:
    """Разослать объявление о рейсе по подключённым чатам.

    Возвращает количество чатов, в которые ушло объявление.
    """
    chats = await get_target_chats(session, flight)
    if not chats:
        return 0

    traveler = await session.get(User, flight.traveler_id)
    if not traveler:
        return 0

    # Рейтинг в объявлении — главное отличие от обычного поста в чате
    rating = f"⭐ {traveler.rating:.1f} ({traveler.reviews_count})" if traveler.reviews_count else ""

    text = nt(
        "ru", "crosspost_flight",
        from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
        available_kg=flight.available_kg, price_per_kg=flight.price_per_kg,
        traveler_name=traveler.full_name, traveler_rating=rating,
    )
    markup = _announcement_markup(flight.id)

    for chat in chats:
        # Каждое объявление уходит в фоне: рассылка не должна задерживать ответ API
        fire_and_forget(send_message(chat.chat_id, text, reply_markup=markup))
        chat.posts_count = (chat.posts_count or 0) + 1

    await session.commit()
    logger.info("[CROSSPOST] Рейс %s разослан в чаты: %s", flight.id, len(chats))
    return len(chats)


async def add_chat(
    session: AsyncSession, chat_id: int, title: str | None, added_by: int | None,
) -> PromoChat:
    """Подключить чат к рассылке рейсов."""
    existing = (await session.execute(
        select(PromoChat).where(PromoChat.chat_id == chat_id)
    )).scalar_one_or_none()

    # Повторное подключение просто включает чат обратно
    if existing:
        existing.is_active = True
        existing.title = title or existing.title
        await session.commit()
        return existing

    chat = PromoChat(chat_id=chat_id, title=title, added_by=added_by, is_active=True)
    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    logger.info("[CROSSPOST] Чат подключён: %s (%s)", chat_id, title)
    return chat


async def remove_chat(session: AsyncSession, chat_id: int) -> bool:
    """Отключить чат от рассылки. Запись остаётся ради истории."""
    chat = (await session.execute(
        select(PromoChat).where(PromoChat.chat_id == chat_id)
    )).scalar_one_or_none()
    if not chat:
        return False

    chat.is_active = False
    await session.commit()
    logger.info("[CROSSPOST] Чат отключён: %s", chat_id)
    return True
