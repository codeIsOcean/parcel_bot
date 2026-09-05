"""Тесты оплаты звёздами: контракт payload и зачисление."""

import pytest

from backend.app.config import settings
from backend.app.services import balance_service, payment_service
from shared.models.user import User


async def add_user(session, user_id: int = 1) -> User:
    """Пользователь с нулевым балансом."""
    user = User(id=user_id, first_name="Тест", lang="ru")
    session.add(user)
    await session.commit()
    return user


def test_allowed_amounts_from_config():
    """Разрешены только суммы из пакетов конфига."""
    package = settings.topup_packages[0]
    assert payment_service.is_allowed_amount(package) is True
    assert payment_service.is_allowed_amount(package + 1) is False


def test_payload_roundtrip():
    """payload разбирается обратно в пользователя и сумму."""
    parsed = payment_service.parse_topup_payload("topup:12345:250")
    assert parsed == (12345, 250)


def test_payload_rejects_foreign_prefix():
    """Чужой префикс не принимается."""
    assert payment_service.parse_topup_payload("sub:1:250") is None
    assert payment_service.parse_topup_payload("мусор") is None


def test_validate_rejects_unlisted_amount():
    """Сумма вне пакетов отклоняется до списания."""
    ok, error = payment_service.validate_topup_payload("topup:1:37")
    assert ok is False
    assert error


def test_validate_accepts_package():
    """Сумма из пакета проходит проверку."""
    package = settings.topup_packages[0]
    ok, error = payment_service.validate_topup_payload(f"topup:1:{package}")
    assert ok is True
    assert error == ""


@pytest.mark.asyncio
async def test_complete_topup_credits_balance(session):
    """Успешная оплата зачисляет звёзды."""
    await add_user(session)
    package = settings.topup_packages[0]

    result = await payment_service.complete_stars_topup(
        session, f"topup:1:{package}", "CHARGE_1",
    )
    assert result.ok is True
    assert await balance_service.get_balance(session, 1) == package


@pytest.mark.asyncio
async def test_complete_topup_is_idempotent(session):
    """Повторная доставка события не удваивает баланс."""
    await add_user(session)
    package = settings.topup_packages[0]

    await payment_service.complete_stars_topup(session, f"topup:1:{package}", "CHARGE_1")
    await payment_service.complete_stars_topup(session, f"topup:1:{package}", "CHARGE_1")

    assert await balance_service.get_balance(session, 1) == package


@pytest.mark.asyncio
async def test_complete_topup_rejects_bad_amount(session):
    """Сумма вне пакетов не зачисляется, даже если событие пришло."""
    await add_user(session)

    result = await payment_service.complete_stars_topup(session, "topup:1:37", "CHARGE_2")
    assert result.ok is False
    assert await balance_service.get_balance(session, 1) == 0


def test_stars_to_usd_uses_config_rate():
    """Пересчёт в доллары идёт по курсу из конфига."""
    assert payment_service.stars_to_usd(100) == round(100 * settings.star_usd_rate, 2)
