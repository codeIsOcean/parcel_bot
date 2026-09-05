"""Тесты дневного тарифа перевозчика."""

from datetime import date, timedelta

import pytest

from backend.app.config import settings
from backend.app.services import access_service, balance_service
from backend.app.services.access_service import PaymentRequiredError
from shared.models.user import User

TODAY = date.today()


async def add_traveler(session, trial_days: int = 0, balance: int = 0) -> User:
    """Перевозчик с заданным пробным остатком и балансом."""
    user = User(id=1, first_name="Перевозчик", lang="ru", trial_days_left=trial_days)
    session.add(user)
    await session.commit()

    if balance:
        await balance_service.top_up(session, user.id, balance, external_ref="seed")
        await session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def no_launch_trial(monkeypatch):
    """Общий пробный период запуска выключен: проверяем платную логику."""
    monkeypatch.setattr(settings, "free_access_until", "")
    monkeypatch.setattr(settings, "daily_fee_stars", 30)


@pytest.mark.asyncio
async def test_new_day_is_closed(session):
    """Пока день не открыт, отвечать нельзя."""
    user = await add_traveler(session)
    assert access_service.day_is_open(user) is False


@pytest.mark.asyncio
async def test_trial_day_is_free(session):
    """Пробный день открывается без списания."""
    user = await add_traveler(session, trial_days=2, balance=100)

    result = await access_service.open_day(session, user)
    assert result.ok is True
    assert result.reason == "trial"
    assert user.trial_days_left == 1
    # Деньги при этом не тронуты
    assert await balance_service.get_balance(session, user.id) == 100


@pytest.mark.asyncio
async def test_day_charged_after_trial(session):
    """Когда пробные дни кончились, списывается дневной тариф."""
    user = await add_traveler(session, trial_days=0, balance=100)

    result = await access_service.open_day(session, user)
    assert result.ok is True
    assert result.reason == "charged"
    assert await balance_service.get_balance(session, user.id) == 70


@pytest.mark.asyncio
async def test_second_call_same_day_is_free(session):
    """Повторное открытие того же дня не списывает второй раз."""
    user = await add_traveler(session, balance=100)

    await access_service.open_day(session, user)
    second = await access_service.open_day(session, user)

    assert second.reason == "already"
    assert await balance_service.get_balance(session, user.id) == 70


@pytest.mark.asyncio
async def test_day_blocked_without_funds(session):
    """Без денег день не открывается и баланс не уходит в минус."""
    user = await add_traveler(session, balance=10)

    result = await access_service.open_day(session, user)
    assert result.ok is False
    assert result.reason == "insufficient"
    assert await balance_service.get_balance(session, user.id) == 10

    with pytest.raises(PaymentRequiredError):
        await access_service.ensure_can_respond(session, user)


@pytest.mark.asyncio
async def test_idle_day_costs_nothing(session):
    """День без активности пробный остаток не тратит."""
    user = await add_traveler(session, trial_days=3, balance=100)

    # Просто проверка состояния ничего не списывает и не тратит
    assert access_service.day_is_open(user) is False
    assert user.trial_days_left == 3


@pytest.mark.asyncio
async def test_new_day_requires_new_payment(session):
    """Вчерашняя оплата на сегодня не распространяется."""
    user = await add_traveler(session, balance=100)
    user.last_fee_date = TODAY - timedelta(days=1)
    await session.commit()

    assert access_service.day_is_open(user) is False
    result = await access_service.open_day(session, user)
    assert result.reason == "charged"


def test_launch_trial_off_when_unset():
    """Пустая настройка не открывает бесплатный доступ."""
    assert access_service.launch_trial_active() is False


def test_launch_trial_off_on_broken_value(monkeypatch):
    """Кривая дата тоже не открывает доступ."""
    monkeypatch.setattr(settings, "free_access_until", "не-дата")
    assert access_service.launch_trial_active() is False


def test_launch_trial_window(monkeypatch):
    """В последний день периода запуска доступ ещё открыт."""
    monkeypatch.setattr(settings, "free_access_until", "2026-10-01")
    assert access_service.launch_trial_active(today=date(2026, 10, 1)) is True
    assert access_service.launch_trial_active(today=date(2026, 10, 2)) is False


@pytest.mark.asyncio
async def test_launch_trial_spends_nothing(session, monkeypatch):
    """Во время периода запуска не тратятся ни деньги, ни пробные дни."""
    monkeypatch.setattr(settings, "free_access_until", "2099-01-01")
    user = await add_traveler(session, trial_days=3, balance=100)

    result = await access_service.open_day(session, user)
    assert result.reason == "launch_trial"
    assert user.trial_days_left == 3
    assert await balance_service.get_balance(session, user.id) == 100


@pytest.mark.asyncio
async def test_access_state_shape(session):
    """Фронту нужен полный набор полей, чтобы нарисовать замок и кнопку."""
    user = await add_traveler(session, trial_days=5)
    state = access_service.access_state(user)

    assert set(state) == {
        "can_respond", "day_paid", "launch_trial",
        "trial_days_left", "daily_fee_stars", "balance_stars",
    }
    assert state["trial_days_left"] == 5
    assert state["can_respond"] is False
