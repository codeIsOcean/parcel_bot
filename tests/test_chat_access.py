"""Тесты права писать в чат: отправитель бесплатно, перевозчик по дневному тарифу."""

from datetime import date, timedelta

import pytest

from backend.app.config import settings
from backend.app.services import access_service, balance_service
from backend.app.services.access_service import PaymentRequiredError
from shared.models.flight import Flight, FlightStatus
from shared.models.match import Match, MatchStatus
from shared.models.parcel import Parcel, ParcelSize, ParcelStatus
from shared.models.user import User

SENDER_ID = 1
TRAVELER_ID = 2


@pytest.fixture(autouse=True)
def paid_mode(monkeypatch):
    """Платный режим: период запуска выключен, тариф известен."""
    monkeypatch.setattr(settings, "free_access_until", "")
    monkeypatch.setattr(settings, "daily_fee_stars", 30)


async def setup_chat(session, trial_days: int = 0, balance: int = 0):
    """Посылка, заявка и рейс. Перевозчику задаём пробные дни и баланс."""
    sender = User(id=SENDER_ID, first_name="Отправитель", lang="ru")
    traveler = User(id=TRAVELER_ID, first_name="Перевозчик", lang="ru", trial_days_left=trial_days)
    session.add_all([sender, traveler])

    parcel = Parcel(
        sender_id=SENDER_ID, from_city="Dubai", to_city="Almaty",
        description="Документы", weight=2.0, size=ParcelSize.SMALL,
        price=25.0, status=ParcelStatus.PENDING,
    )
    flight = Flight(
        traveler_id=TRAVELER_ID, from_city="Dubai", to_city="Almaty",
        flight_date=date.today() + timedelta(days=3),
        available_kg=10.0, total_kg=10.0, price_per_kg=9.0,
        status=FlightStatus.ACTIVE,
    )
    session.add_all([parcel, flight])
    await session.commit()

    session.add(Match(parcel_id=parcel.id, flight_id=flight.id, status=MatchStatus.PENDING))
    await session.commit()

    if balance:
        await balance_service.top_up(session, TRAVELER_ID, balance, external_ref="seed")
        await session.refresh(traveler)

    return sender, traveler, parcel


@pytest.mark.asyncio
async def test_sender_writes_for_free(session):
    """Отправитель обсуждает свою посылку бесплатно и день ему не нужен."""
    sender, _, parcel = await setup_chat(session)
    await access_service.ensure_can_write(session, sender, parcel.id)


@pytest.mark.asyncio
async def test_traveler_blocked_without_day(session):
    """Перевозчик без открытого дня и без денег писать не может."""
    _, traveler, parcel = await setup_chat(session)
    with pytest.raises(PaymentRequiredError):
        await access_service.ensure_can_write(session, traveler, parcel.id)


@pytest.mark.asyncio
async def test_traveler_writes_on_trial_day(session):
    """Пробный день открывает переписку и тратится один раз."""
    _, traveler, parcel = await setup_chat(session, trial_days=2)

    await access_service.ensure_can_write(session, traveler, parcel.id)
    await access_service.ensure_can_write(session, traveler, parcel.id)

    # Второе сообщение в тот же день второй пробный день не съедает
    assert traveler.trial_days_left == 1


@pytest.mark.asyncio
async def test_traveler_writes_after_charge(session):
    """С балансом день оплачивается и переписка открывается."""
    _, traveler, parcel = await setup_chat(session, balance=100)

    await access_service.ensure_can_write(session, traveler, parcel.id)
    assert await balance_service.get_balance(session, TRAVELER_ID) == 70


@pytest.mark.asyncio
async def test_launch_trial_opens_chat(session, monkeypatch):
    """В период запуска пишут все и ничего не тратится."""
    monkeypatch.setattr(settings, "free_access_until", "2099-01-01")
    _, traveler, parcel = await setup_chat(session, trial_days=3)

    await access_service.ensure_can_write(session, traveler, parcel.id)
    assert traveler.trial_days_left == 3


@pytest.mark.asyncio
async def test_chat_without_parcel_is_open(session):
    """Чат без привязки к посылке не ограничиваем."""
    sender, _, _ = await setup_chat(session)
    await access_service.ensure_can_write(session, sender, None)
