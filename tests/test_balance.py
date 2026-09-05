"""Тесты баланса в звёздах."""

import pytest

from backend.app.services import balance_service
from shared.models.balance import BalanceTxnKind
from shared.models.user import User


async def add_user(session, user_id: int = 1) -> User:
    """Пользователь с нулевым балансом."""
    user = User(id=user_id, first_name="Тест", lang="ru")
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_topup_increases_balance(session):
    """Пополнение увеличивает баланс и пишется в журнал."""
    await add_user(session)

    result = await balance_service.top_up(session, 1, 250, external_ref="stars:A1")
    assert result.ok is True
    assert result.balance == 250

    entries = await balance_service.history(session, 1)
    assert len(entries) == 1
    assert entries[0].kind == BalanceTxnKind.TOPUP
    assert entries[0].balance_after == 250


@pytest.mark.asyncio
async def test_topup_is_idempotent(session):
    """Повторное событие с тем же ключом не зачисляется дважды."""
    await add_user(session)

    await balance_service.top_up(session, 1, 250, external_ref="stars:A1")
    second = await balance_service.top_up(session, 1, 250, external_ref="stars:A1")

    assert second.reason == "duplicate"
    assert await balance_service.get_balance(session, 1) == 250


@pytest.mark.asyncio
async def test_charge_reduces_balance(session):
    """Списание уменьшает баланс."""
    await add_user(session)
    await balance_service.top_up(session, 1, 250, external_ref="stars:A1")

    result = await balance_service.charge(session, 1, 150, external_ref="post:7")
    assert result.ok is True
    assert result.balance == 100


@pytest.mark.asyncio
async def test_charge_blocked_without_funds(session):
    """Списание без денег не проходит и баланс не трогает."""
    await add_user(session)
    await balance_service.top_up(session, 1, 100, external_ref="stars:A1")

    result = await balance_service.charge(session, 1, 150, external_ref="post:7")
    assert result.ok is False
    assert result.reason == "insufficient"
    assert await balance_service.get_balance(session, 1) == 100


@pytest.mark.asyncio
async def test_charge_is_idempotent(session):
    """Повторная оплата той же публикации не списывает дважды."""
    await add_user(session)
    await balance_service.top_up(session, 1, 400, external_ref="stars:A1")

    await balance_service.charge(session, 1, 150, external_ref="post:7")
    second = await balance_service.charge(session, 1, 150, external_ref="post:7")

    assert second.reason == "duplicate"
    assert await balance_service.get_balance(session, 1) == 250


@pytest.mark.asyncio
async def test_negative_amount_rejected(session):
    """Отрицательные и нулевые суммы не принимаются."""
    await add_user(session)
    assert (await balance_service.top_up(session, 1, 0)).reason == "bad_amount"
    assert (await balance_service.charge(session, 1, -5)).reason == "bad_amount"


@pytest.mark.asyncio
async def test_topup_unknown_user(session):
    """Пополнение несуществующему пользователю не проходит."""
    result = await balance_service.top_up(session, 999, 100, external_ref="stars:X")
    assert result.ok is False
    assert result.reason == "user_not_found"


@pytest.mark.asyncio
async def test_refund_marked_separately(session):
    """Возврат отличается от обычного пополнения в журнале."""
    await add_user(session)
    await balance_service.refund(session, 1, 150, external_ref="refund:post:7")

    entries = await balance_service.history(session, 1)
    assert entries[0].kind == BalanceTxnKind.REFUND
