"""Тесты подбора рейсов и посылок друг под друга."""

from datetime import date, timedelta

import pytest

from backend.app.services import notification_service
from shared.models.flight import Flight, FlightStatus
from shared.models.parcel import Parcel, ParcelSize, ParcelStatus
from shared.models.user import User

TODAY = date.today()


async def add_user(session, user_id: int, name: str = "Тест") -> User:
    """Создать пользователя."""
    user = User(id=user_id, first_name=name, lang="ru")
    session.add(user)
    await session.commit()
    return user


async def add_flight(session, traveler_id: int, **kwargs) -> Flight:
    """Создать рейс с разумными значениями по умолчанию."""
    flight = Flight(
        traveler_id=traveler_id,
        from_city=kwargs.get("from_city", "Dubai"),
        to_city=kwargs.get("to_city", "Almaty"),
        flight_date=kwargs.get("flight_date", TODAY + timedelta(days=5)),
        available_kg=kwargs.get("available_kg", 10.0),
        total_kg=kwargs.get("available_kg", 10.0),
        price_per_kg=kwargs.get("price_per_kg", 9.0),
        status=kwargs.get("status", FlightStatus.ACTIVE),
    )
    session.add(flight)
    await session.commit()
    return flight


async def add_parcel(session, sender_id: int, **kwargs) -> Parcel:
    """Создать посылку с разумными значениями по умолчанию."""
    parcel = Parcel(
        sender_id=sender_id,
        from_city=kwargs.get("from_city", "Dubai"),
        to_city=kwargs.get("to_city", "Almaty"),
        description=kwargs.get("description", "Документы"),
        weight=kwargs.get("weight", 3.0),
        size=ParcelSize.SMALL,
        price=kwargs.get("price", 30.0),
        status=kwargs.get("status", ParcelStatus.PENDING),
    )
    session.add(parcel)
    await session.commit()
    return parcel


@pytest.mark.asyncio
async def test_finds_matching_flight(session):
    """Рейс по тому же маршруту с достаточным весом подходит посылке."""
    await add_user(session, 1)
    await add_user(session, 2)
    await add_flight(session, traveler_id=2)
    parcel = await add_parcel(session, sender_id=1)

    flights = await notification_service.find_flights_for_parcel(session, parcel)
    assert len(flights) == 1


@pytest.mark.asyncio
async def test_skips_flight_without_capacity(session):
    """Рейс, куда посылка не влезает по весу, не предлагаем."""
    await add_user(session, 1)
    await add_user(session, 2)
    await add_flight(session, traveler_id=2, available_kg=1.0)
    parcel = await add_parcel(session, sender_id=1, weight=5.0)

    assert await notification_service.find_flights_for_parcel(session, parcel) == []


@pytest.mark.asyncio
async def test_skips_past_flight(session):
    """Улетевший рейс не предлагаем."""
    await add_user(session, 1)
    await add_user(session, 2)
    await add_flight(session, traveler_id=2, flight_date=TODAY - timedelta(days=1))
    parcel = await add_parcel(session, sender_id=1)

    assert await notification_service.find_flights_for_parcel(session, parcel) == []


@pytest.mark.asyncio
async def test_skips_own_flight(session):
    """Свой же рейс отправителю не предлагаем."""
    await add_user(session, 1)
    await add_flight(session, traveler_id=1)
    parcel = await add_parcel(session, sender_id=1)

    assert await notification_service.find_flights_for_parcel(session, parcel) == []


@pytest.mark.asyncio
async def test_skips_other_route(session):
    """Другой маршрут не подходит."""
    await add_user(session, 1)
    await add_user(session, 2)
    await add_flight(session, traveler_id=2, to_city="Astana")
    parcel = await add_parcel(session, sender_id=1)

    assert await notification_service.find_flights_for_parcel(session, parcel) == []


@pytest.mark.asyncio
async def test_finds_waiting_parcels_for_new_flight(session):
    """Новый рейс подхватывает посылки, которые давно ждут маршрут."""
    await add_user(session, 1)
    await add_user(session, 2)
    await add_parcel(session, sender_id=1, weight=3.0)
    await add_parcel(session, sender_id=1, weight=20.0)          # не влезает
    await add_parcel(session, sender_id=1, status=ParcelStatus.ACCEPTED)  # уже везут
    flight = await add_flight(session, traveler_id=2, available_kg=10.0)

    parcels = await notification_service.find_parcels_for_flight(session, flight)
    assert len(parcels) == 1
    assert parcels[0].weight == 3.0


@pytest.mark.asyncio
async def test_rating_hidden_for_newcomer(session):
    """У новичка без отзывов подписи с рейтингом быть не должно."""
    user = await add_user(session, 1)
    assert notification_service.format_rating(user) == ""

    user.rating = 4.75
    user.reviews_count = 12
    assert notification_service.format_rating(user) == "⭐ 4.8 (12)"
