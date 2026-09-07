"""Тесты кросс-постинга рейсов и посылок по чатам и реестра групп."""

from datetime import date, timedelta

import pytest

from backend.app.services import crosspost_service
from shared.models.flight import Flight, FlightStatus
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.promo_chat import GroupPost, PromoChat
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

    chats = await crosspost_service.get_target_chats(session, flight.from_city, flight.to_city, crosspost_service.KIND_FLIGHT)
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

    chats = await crosspost_service.get_target_chats(session, flight.from_city, flight.to_city, crosspost_service.KIND_FLIGHT)
    assert [c.chat_id for c in chats] == [-1]


@pytest.mark.asyncio
async def test_announce_counts_target_chats(session):
    """Рассылка возвращает число чатов, в которые ушло объявление."""
    flight = await add_flight(session)
    session.add(PromoChat(chat_id=-1, is_active=True))
    await session.commit()

    assert await crosspost_service.announce_flight(session, flight) == 1


@pytest.mark.asyncio
async def test_target_chats_respect_kind_and_membership(session):
    """Чат «только рейсы» посылок не получает; чат без бота — ничего."""
    session.add_all([
        PromoChat(chat_id=-1, post_parcels=False, post_flights=True),
        PromoChat(chat_id=-2, post_parcels=True, post_flights=False),
        PromoChat(chat_id=-3, is_member=False),
    ])
    await session.commit()

    parcels = await crosspost_service.get_target_chats(session, "Dubai", "Almaty", crosspost_service.KIND_PARCEL)
    flights = await crosspost_service.get_target_chats(session, "Dubai", "Almaty", crosspost_service.KIND_FLIGHT)
    assert [c.chat_id for c in parcels] == [-2]
    assert [c.chat_id for c in flights] == [-1]


@pytest.mark.asyncio
async def test_parcel_for_specific_traveler_not_announced(session):
    """Посылка, адресованная конкретному перевозчику, в группы не идёт."""
    session.add_all([User(id=1, first_name="Отправитель"), PromoChat(chat_id=-1)])
    parcel = Parcel(sender_id=1, traveler_id=1, from_city="Dubai", to_city="Almaty",
                    description="Документы", weight=1.0, price=20.0, status=ParcelStatus.PENDING)
    session.add(parcel)
    await session.commit()

    assert await crosspost_service.announce_parcel(session, parcel) == 0
    parcel.traveler_id = None
    await session.commit()
    assert await crosspost_service.announce_parcel(session, parcel) == 1


@pytest.mark.asyncio
async def test_close_posts_marks_once(session):
    """Закрытие помечает посты и второй раз их не трогает."""
    flight = await add_flight(session)
    session.add_all([
        GroupPost(chat_id=-1, message_id=10, kind="flight", entity_id=flight.id),
        GroupPost(chat_id=-2, message_id=11, kind="flight", entity_id=flight.id),
        GroupPost(chat_id=-2, message_id=12, kind="parcel", entity_id=flight.id),
    ])
    await session.commit()

    assert await crosspost_service.close_flight_posts(session, flight) == 2
    assert await crosspost_service.close_flight_posts(session, flight) == 0


def test_parse_group_link_variants():
    """Разбор ссылок: @username, t.me, приватный c/<id>, число, инвайт."""
    parse = crosspost_service.parse_group_link
    assert parse("@parcels_chat") == ("@parcels_chat", None)
    assert parse("https://t.me/parcels_chat") == ("@parcels_chat", None)
    assert parse("t.me/c/123456/77") == (-100123456, None)
    assert parse("-1001234567890") == (-1001234567890, None)
    assert parse("https://t.me/+AbCdEf") == (None, "invite_link")
    assert parse("") == (None, "bad_link")


@pytest.mark.asyncio
async def test_my_chat_member_updates_registry(session):
    """Добавили бота — группа в реестре; выгнали — is_member снят, запись осталась."""
    chat = {"id": -100500, "type": "supergroup", "title": "Посылки Дубай", "username": "dxb_parcels"}
    added = await crosspost_service.on_my_chat_member(session, chat, "member", added_by=7)
    assert added and added.is_member and added.title == "Посылки Дубай" and added.username == "dxb_parcels"

    kicked = await crosspost_service.on_my_chat_member(session, chat, "kicked")
    assert kicked.is_member is False and kicked.id == added.id

    # Личный чат реестру не нужен
    assert await crosspost_service.on_my_chat_member(session, {"id": 5, "type": "private"}, "member") is None


@pytest.mark.asyncio
async def test_announce_without_chats(session):
    """Без подключённых чатов рассылка просто ничего не делает."""
    flight = await add_flight(session)
    assert await crosspost_service.announce_flight(session, flight) == 0
