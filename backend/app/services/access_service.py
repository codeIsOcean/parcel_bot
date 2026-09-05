"""Дневной тариф перевозчика.

Модель монетизации:
  * отправитель не платит никогда — публикация посылки и переписка бесплатны,
    спрос облагать нельзя, иначе маркетплейс не наполнится;
  * перевозчик видит все входящие заявки бесплатно, но чтобы ответить,
    у него должен быть оплачен сегодняшний день;
  * плата списывается один раз в сутки и только в день, когда перевозчик
    реально отвечает. Дни без активности денег не стоят.

Пробный период считается в активных днях, а не в календарных: перевозчик,
который зашёл раз в неделю, потратит один пробный день, а не семь.

Есть ещё общий пробный период на запуск (FREE_ACCESS_UNTIL): пока он идёт,
отвечают все бесплатно и личные пробные дни не тратятся.
"""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services import balance_service
from shared.models.flight import Flight
from shared.models.match import Match
from shared.models.parcel import Parcel
from shared.models.user import User

logger = logging.getLogger(__name__)


class PaymentRequiredError(Exception):
    """Сегодняшний день не оплачен и денег на балансе не хватает."""

    def __init__(self, price_stars: int, balance_stars: int):
        self.price_stars = price_stars
        self.balance_stars = balance_stars
        super().__init__("Daily fee is not paid")


@dataclass
class DayResult:
    """Итог попытки открыть рабочий день."""
    ok: bool
    # launch_trial | already | trial | charged | insufficient
    reason: str
    balance: int = 0
    trial_days_left: int = 0


def launch_trial_active(today: date | None = None) -> bool:
    """Идёт ли общий пробный период запуска, когда бесплатно всем."""
    raw = (settings.free_access_until or "").strip()
    if not raw:
        return False

    try:
        until = date.fromisoformat(raw)
    except ValueError:
        # Кривое значение не должно случайно открыть бесплатный доступ
        logger.error("[ACCESS] Некорректный FREE_ACCESS_UNTIL=%r, период выключен", raw)
        return False

    return (today or date.today()) <= until


def day_is_open(user: User, today: date | None = None) -> bool:
    """Оплачен ли у перевозчика сегодняшний день."""
    if launch_trial_active(today):
        return True
    return user.last_fee_date == (today or date.today())


async def open_day(
    session: AsyncSession, user: User, today: date | None = None,
) -> DayResult:
    """Открыть перевозчику рабочий день.

    Порядок такой: общий пробный период, затем уже открытый день, затем
    личные пробные дни, и только потом списание с баланса.
    """
    today = today or date.today()

    # Общий пробный период запуска: не тратим ни дни, ни деньги
    if launch_trial_active(today):
        return DayResult(
            ok=True, reason="launch_trial",
            balance=user.balance_stars or 0,
            trial_days_left=user.trial_days_left or 0,
        )

    # День уже открыт — повторно не списываем
    if user.last_fee_date == today:
        return DayResult(
            ok=True, reason="already",
            balance=user.balance_stars or 0,
            trial_days_left=user.trial_days_left or 0,
        )

    # Личный пробный день
    if (user.trial_days_left or 0) > 0:
        user.trial_days_left = user.trial_days_left - 1
        user.last_fee_date = today
        await session.commit()

        logger.info("[ACCESS] Пробный день: user=%s, осталось=%s", user.id, user.trial_days_left)
        return DayResult(
            ok=True, reason="trial",
            balance=user.balance_stars or 0,
            trial_days_left=user.trial_days_left,
        )

    # Платный день. Ключ идемпотентности — пользователь и дата.
    result = await balance_service.charge(
        session, user.id, settings.daily_fee_stars,
        external_ref=f"day:{user.id}:{today.isoformat()}",
        note=f"Дневной тариф перевозчика за {today.isoformat()}",
    )

    if not result.ok:
        logger.info("[ACCESS] Не хватает звёзд на день: user=%s, баланс=%s", user.id, result.balance)
        return DayResult(ok=False, reason="insufficient", balance=result.balance)

    user.last_fee_date = today
    await session.commit()

    logger.info("[ACCESS] День оплачен: user=%s, остаток=%s", user.id, result.balance)
    return DayResult(ok=True, reason="charged", balance=result.balance)


async def ensure_can_respond(session: AsyncSession, user: User) -> None:
    """Открыть день или отказать, если денег нет."""
    result = await open_day(session, user)
    if result.ok:
        return
    raise PaymentRequiredError(settings.daily_fee_stars, result.balance)


async def ensure_can_write(session: AsyncSession, user: User, parcel_id: int | None) -> None:
    """Проверить право писать в чат по посылке.

    Отправитель пишет всегда бесплатно. Перевозчик — только когда у него
    открыт сегодняшний рабочий день.
    """
    # Чат без привязки к посылке не ограничиваем
    if not parcel_id:
        return

    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        return

    # Свою посылку отправитель обсуждает бесплатно
    if parcel.sender_id == user.id:
        return

    # Ограничение касается только той стороны, которая везёт
    is_traveler = parcel.traveler_id == user.id
    if not is_traveler:
        # Перевозчика могли ещё не назначить — смотрим, откликался ли он рейсом
        flight = (await session.execute(
            select(Flight)
            .join(Match, Match.flight_id == Flight.id)
            .where(Match.parcel_id == parcel_id, Flight.traveler_id == user.id)
            .limit(1)
        )).scalar_one_or_none()
        is_traveler = flight is not None

    if is_traveler:
        await ensure_can_respond(session, user)


def access_state(user: User) -> dict:
    """Состояние доступа для фронта — им рисуется замок и кнопка оплаты дня."""
    return {
        "can_respond": day_is_open(user),
        "day_paid": user.last_fee_date == date.today(),
        "launch_trial": launch_trial_active(),
        "trial_days_left": user.trial_days_left or 0,
        "daily_fee_stars": settings.daily_fee_stars,
        "balance_stars": user.balance_stars or 0,
    }
