import logging
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from shared.models.match import Match, MatchStatus
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.flight import Flight
from shared.models.user import User

logger = logging.getLogger(__name__)


async def create_match(
    session: AsyncSession,
    parcel_id: int,
    flight_id: int,
    sender_id: int | None = None,
) -> Match:
    """Создать заявку (связь посылка↔рейс)."""
    logger.info("[MATCH] Создание: parcel=%s, flight=%s, sender=%s", parcel_id, flight_id, sender_id)

    # Проверяем что посылка существует и принадлежит отправителю
    parcel = (await session.execute(
        select(Parcel).where(Parcel.id == parcel_id)
    )).scalar_one_or_none()
    if not parcel:
        raise ValueError("Parcel not found")
    if sender_id and parcel.sender_id != sender_id:
        raise ValueError("Not authorized: not the parcel owner")

    # Проверяем что нет дубля
    existing = await session.execute(
        select(Match).where(
            and_(Match.parcel_id == parcel_id, Match.flight_id == flight_id)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Match already exists")

    match = Match(
        parcel_id=parcel_id,
        flight_id=flight_id,
        status=MatchStatus.PENDING,
    )
    session.add(match)

    # Инкрементируем счётчик заявок на рейс при создании
    flight = (await session.execute(
        select(Flight).where(Flight.id == flight_id)
    )).scalar_one_or_none()
    if flight:
        flight.requests_count = (flight.requests_count or 0) + 1

    await session.commit()
    await session.refresh(match)

    logger.info("[MATCH] Создан: match_id=%s", match.id)
    return match


async def get_flight_requests(
    session: AsyncSession,
    flight_id: int,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """Получить заявки на рейс с данными посылки и отправителя."""
    query = (
        select(Match, Parcel, User)
        .join(Parcel, Match.parcel_id == Parcel.id)
        .join(User, Parcel.sender_id == User.id)
        .where(Match.flight_id == flight_id)
        .order_by(Match.created_at.desc())
    )

    # Считаем количество
    count_q = select(func.count()).select_from(
        select(Match.id).where(Match.flight_id == flight_id).subquery()
    )
    total = (await session.execute(count_q)).scalar() or 0

    # Пагинация
    query = query.offset((page - 1) * limit).limit(limit)
    result = await session.execute(query)
    rows = result.all()

    requests = []
    for match, parcel, sender in rows:
        requests.append({
            "id": match.id,
            "status": match.status.value,
            "created_at": match.created_at,
            "parcel": {
                "id": parcel.id,
                "from_city": parcel.from_city,
                "to_city": parcel.to_city,
                "description": parcel.description,
                "weight": parcel.weight,
                "price": parcel.price,
                "status": parcel.status.value,
            },
            "sender": {
                "id": sender.id,
                "name": sender.full_name,
                "rating": sender.rating,
                "deliveries_count": sender.deliveries_count,
            },
        })

    return requests, total


async def accept_match(
    session: AsyncSession,
    match_id: int,
    traveler_id: int,
) -> Match:
    """Принять заявку — привязать посылку к перевозчику."""
    # Загружаем match с рейсом
    result = await session.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise ValueError("Match not found")

    # Проверяем что заявка в статусе PENDING
    if match.status != MatchStatus.PENDING:
        raise ValueError(f"Cannot accept match in status {match.status.value}")

    # Проверяем что рейс принадлежит перевозчику
    flight_result = await session.execute(
        select(Flight).where(Flight.id == match.flight_id)
    )
    flight = flight_result.scalar_one_or_none()
    if not flight or flight.traveler_id != traveler_id:
        raise ValueError("Not authorized")

    # Обновляем статус заявки
    match.status = MatchStatus.ACCEPTED

    # Обновляем посылку — привязываем перевозчика
    parcel_result = await session.execute(
        select(Parcel).where(Parcel.id == match.parcel_id)
    )
    parcel = parcel_result.scalar_one_or_none()
    if not parcel:
        raise ValueError("Parcel not found")

    # Защита от двойного принятия — посылка уже взята другим перевозчиком
    if parcel.status != ParcelStatus.PENDING:
        raise ValueError("Parcel is already accepted by another traveler")

    parcel.traveler_id = traveler_id
    parcel.status = ParcelStatus.ACCEPTED
        # Уменьшаем доступный вес рейса
        if flight and parcel.weight:
            flight.available_kg = max(0, flight.available_kg - parcel.weight)

    await session.commit()
    await session.refresh(match)

    logger.info("[MATCH] Принят: match=%s, traveler=%s", match_id, traveler_id)
    return match


async def decline_match(
    session: AsyncSession,
    match_id: int,
    traveler_id: int,
) -> Match:
    """Отклонить заявку."""
    result = await session.execute(
        select(Match).where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise ValueError("Match not found")

    # Проверяем что заявка в статусе PENDING
    if match.status != MatchStatus.PENDING:
        raise ValueError(f"Cannot decline match in status {match.status.value}")

    # Проверяем что рейс принадлежит перевозчику
    flight_result = await session.execute(
        select(Flight).where(Flight.id == match.flight_id)
    )
    flight = flight_result.scalar_one_or_none()
    if not flight or flight.traveler_id != traveler_id:
        raise ValueError("Not authorized")

    match.status = MatchStatus.DECLINED
    await session.commit()
    await session.refresh(match)

    logger.info("[MATCH] Отклонён: match=%s, traveler=%s", match_id, traveler_id)
    return match
