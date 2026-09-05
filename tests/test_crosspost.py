"""Тесты кросс-постинга рейсов по чатам."""

from datetime import date, timedelta

import pytest

from backend.app.services import crosspost_service
from shared.models.flight import Flight, FlightStatus
from shared.models.promo_chat import PromoChat
from shared.models.user import User


async def add_flight(session) -> Flight:
    """Рейс Dubai → Almaty."""
    session.add(User(id=1, first_name="Перевозчик", lang="ru"))
    flight = Flight(
        traveler_id=1,
        from_city="Dubai",
        to_city="Almaty",
        flight_date=date.today() + timedelta(days=3),
        available_kg=10.0,
        total_kg=10.0,
        price_per_kg=9.0,
        status=FlightStatus.ACTIVE,
    )
    session.add(flight)
    await session.commit()
    await session.refresh(flight)
    return flight


def test_chat_without_filter_takes_everything():
    """Чат без фильтра городов получает все рейсы."""
    chat = PromoChat(chat_id=-100, cities=None)
    assert chat.matches_route("Dubai", "Almaty") is True


def test_chat_filter_matches_either_city():
    """Фильтр срабатывает, если совпал город отправления или назначения."""
    chat = PromoChat(chat_id=-100, cities="Almaty, Astana")
    assert chat.matches_route("Dubai", "Almaty") is True
    assert chat.matches_route("Astana", "Dubai") is True
    assert chat.matches_route("Moscow", "Paris") is False


def test_chat_filter_ignores_case():
    """Регистр в фильтре не важен."""
    chat = PromoChat(chat_id=-100, cities="almaty")
    assert chat.matches_route("Dubai", "ALMATY") is True


@pytest.mark.asyncio
async def test_target_chats_skip_inactive(session):
    """Отключённый чат в рассылку не попадает."""
    flight = await add_flight(session)
    session.add_all([
        PromoChat(chat_id=-1, is_active=True),
        PromoChat(chat_id=-2, is_active=False),
    ])
    await session.commit()

    chats = await crosspost_service.get_target_chats(session, flight)
    assert [c.chat_id for c in chats] == [-1]


@pytest.mark.asyncio
async def test_target_chats_respect_city_filter(session):
    """Чат с чужим маршрутом объявление не получает."""
    flight = await add_flight(session)
    session.add_all([
        PromoChat(chat_id=-1, is_active=True, cities="Almaty"),
        PromoChat(chat_id=-2, is_active=True, cities="Paris"),
    ])
    await session.commit()

    chats = await crosspost_service.get_target_chats(session, flight)
    assert [c.chat_id for c in chats] == [-1]


@pytest.mark.asyncio
async def test_announce_counts_posts(session):
    """После рассылки у чата растёт счётчик объявлений."""
    flight = await add_flight(session)
    chat = PromoChat(chat_id=-1, is_active=True)
    session.add(chat)
    await session.commit()

    sent = await crosspost_service.announce_flight(session, flight)
    assert sent == 1

    await session.refresh(chat)
    assert chat.posts_count == 1


@pytest.mark.asyncio
async def test_announce_without_chats(session):
    """Без подключённых чатов рассылка просто ничего не делает."""
    flight = await add_flight(session)
    assert await crosspost_service.announce_flight(session, flight) == 0
