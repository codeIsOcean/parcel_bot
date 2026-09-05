"""Баланс пользователя в Telegram Stars.

Перевозчик пополняет баланс звёздами или монетами TON, а с баланса
списывается плата за публикацию рейса. Баланс выбран вместо разовой оплаты
каждой публикации, потому что счёт в Telegram выставляется в звёздах и мелкие
платежи по три доллара неудобны и пользователю, и в учёте.

Две гарантии, ради которых здесь всё написано именно так:
  * идемпотентность — повторная доставка одного события Telegram или одна и та
    же транзакция TON не зачислят деньги дважды (unique на external_ref);
  * отсутствие гонок — списание и пополнение берут строку пользователя под
    блокировку, поэтому два параллельных запроса не спишут дважды.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.balance import BalanceTransaction, BalanceTxnKind
from shared.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class BalanceResult:
    """Итог операции с балансом."""
    ok: bool
    balance: int
    # ok | duplicate | insufficient | user_not_found | bad_amount
    reason: str = "ok"
    amount: int = 0


async def _get_user_locked(session: AsyncSession, user_id: int) -> User | None:
    """Загрузить пользователя под блокировкой строки.

    Блокировка сериализует параллельные операции над одним балансом.
    SQLite её не поддерживает, поэтому там работаем без неё: в тестах
    параллельных запросов нет.
    """
    query = select(User).where(User.id == user_id)
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    return (await session.execute(query)).scalar_one_or_none()


async def get_balance(session: AsyncSession, user_id: int) -> int:
    """Текущий баланс в звёздах."""
    user = await session.get(User, user_id)
    return user.balance_stars if user else 0


async def top_up(
    session: AsyncSession,
    user_id: int,
    amount_stars: int,
    external_ref: str | None = None,
    note: str | None = None,
) -> BalanceResult:
    """Зачислить звёзды на баланс."""
    if amount_stars <= 0:
        return BalanceResult(ok=False, balance=0, reason="bad_amount")

    # Событие с таким идентификатором уже проводили — второй раз не зачисляем
    if external_ref:
        existing = (await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.external_ref == external_ref)
        )).scalar_one_or_none()
        if existing:
            logger.info("[BALANCE] Повторное событие пропущено: ref=%s", external_ref)
            return BalanceResult(
                ok=True, balance=existing.balance_after, reason="duplicate", amount=0,
            )

    user = await _get_user_locked(session, user_id)
    if not user:
        return BalanceResult(ok=False, balance=0, reason="user_not_found")

    user.balance_stars = (user.balance_stars or 0) + amount_stars
    session.add(BalanceTransaction(
        user_id=user_id,
        kind=BalanceTxnKind.TOPUP,
        amount_stars=amount_stars,
        balance_after=user.balance_stars,
        external_ref=external_ref,
        note=note,
    ))

    try:
        await session.commit()
    except IntegrityError:
        # Гонка двух одинаковых событий: победила первая запись
        await session.rollback()
        logger.info("[BALANCE] Дубликат перехвачен базой: ref=%s", external_ref)
        return BalanceResult(
            ok=True, balance=await get_balance(session, user_id), reason="duplicate",
        )

    logger.info("[BALANCE] Пополнение: user=%s, +%s ⭐, остаток=%s",
                user_id, amount_stars, user.balance_stars)
    return BalanceResult(ok=True, balance=user.balance_stars, amount=amount_stars)


async def charge(
    session: AsyncSession,
    user_id: int,
    amount_stars: int,
    external_ref: str | None = None,
    note: str | None = None,
) -> BalanceResult:
    """Списать звёзды с баланса."""
    if amount_stars <= 0:
        return BalanceResult(ok=False, balance=0, reason="bad_amount")

    # Повтор того же списания проводить нельзя
    if external_ref:
        existing = (await session.execute(
            select(BalanceTransaction).where(BalanceTransaction.external_ref == external_ref)
        )).scalar_one_or_none()
        if existing:
            return BalanceResult(
                ok=True, balance=existing.balance_after, reason="duplicate", amount=0,
            )

    user = await _get_user_locked(session, user_id)
    if not user:
        return BalanceResult(ok=False, balance=0, reason="user_not_found")

    # Денег не хватает — операция не проводится вообще
    if (user.balance_stars or 0) < amount_stars:
        return BalanceResult(ok=False, balance=user.balance_stars or 0, reason="insufficient")

    user.balance_stars = user.balance_stars - amount_stars
    session.add(BalanceTransaction(
        user_id=user_id,
        kind=BalanceTxnKind.CHARGE,
        amount_stars=amount_stars,
        balance_after=user.balance_stars,
        external_ref=external_ref,
        note=note,
    ))
    await session.commit()

    logger.info("[BALANCE] Списание: user=%s, -%s ⭐, остаток=%s",
                user_id, amount_stars, user.balance_stars)
    return BalanceResult(ok=True, balance=user.balance_stars, amount=amount_stars)


async def refund(
    session: AsyncSession,
    user_id: int,
    amount_stars: int,
    external_ref: str | None = None,
    note: str | None = None,
) -> BalanceResult:
    """Вернуть звёзды на баланс."""
    result = await top_up(session, user_id, amount_stars, external_ref, note)
    # Тип операции в журнале должен отличаться от обычного пополнения
    if result.ok and result.reason == "ok":
        txn = (await session.execute(
            select(BalanceTransaction)
            .where(BalanceTransaction.user_id == user_id)
            .order_by(BalanceTransaction.id.desc())
            .limit(1)
        )).scalar_one_or_none()
        if txn:
            txn.kind = BalanceTxnKind.REFUND
            await session.commit()
    return result


async def history(session: AsyncSession, user_id: int, limit: int = 50) -> list[BalanceTransaction]:
    """Последние движения по балансу."""
    return list((await session.execute(
        select(BalanceTransaction)
        .where(BalanceTransaction.user_id == user_id)
        .order_by(BalanceTransaction.id.desc())
        .limit(limit)
    )).scalars().all())
