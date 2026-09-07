import logging
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from backend.app.services import chat_service, crosspost_service, notification_service
from backend.app.services.access_service import ensure_can_respond
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

    # Переписку заводим сразу: стороны могут договориться до принятия заявки
    if flight:
        await chat_service.ensure_session_for_match(session, parcel, flight)

    # Перевозчик узнаёт о заявке сразу, даже если Mini App закрыт
    if flight:
        await notification_service.notify_new_request(session, parcel, flight)

    logger.info("[MATCH] Создан: match_id=%s", match.id)
    return match


async def create_offer(
    session: AsyncSession,
    parcel_id: int,
    flight_id: int,
    traveler_id: int,
) -> Match:
    """Перевозчик откликается на посылку своим рейсом (например, из группы).

    Зеркало create_match: инициатор — перевозчик, принимает отправитель.
    """
    logger.info("[MATCH] Отклик: parcel=%s, flight=%s, traveler=%s", parcel_id, flight_id, traveler_id)

    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        raise ValueError("Parcel not found")
    if parcel.status != ParcelStatus.PENDING:
        raise ValueError("Parcel is not pending")
    # Посылка, адресованная другому перевозчику, чужие отклики не принимает
    if parcel.traveler_id and parcel.traveler_id != traveler_id:
        raise ValueError("Parcel is reserved for another traveler")
    if parcel.sender_id == traveler_id:
        raise ValueError("Cannot respond to own parcel")

    flight = await session.get(Flight, flight_id)
    if not flight or flight.traveler_id != traveler_id:
        raise ValueError("Not authorized: not the flight owner")

    # Дубль отклика не создаём
    existing = (await session.execute(
        select(Match).where(and_(Match.parcel_id == parcel_id, Match.flight_id == flight_id))
    )).scalar_one_or_none()
    if existing:
        raise ValueError("Match already exists")

    # Отклик — это ответ на заявку, он открывает рабочий день перевозчика
    traveler = await session.get(User, traveler_id)
    if traveler:
        await ensure_can_respond(session, traveler)

    match = Match(parcel_id=parcel_id, flight_id=flight_id, status=MatchStatus.PENDING, initiator="traveler")
    session.add(match)
    await session.commit()
    await session.refresh(match)

    # Переписку заводим сразу, чтобы стороны могли договориться до принятия
    await chat_service.ensure_session_for_match(session, parcel, flight)

    # Отправитель узнаёт об отклике, даже если Mini App закрыт
    await notification_service.notify_offer_received(session, parcel, flight)

    logger.info("[MATCH] Отклик создан: match_id=%s", match.id)
    return match


async def get_parcel_offers(session: AsyncSession, parcel_id: int) -> list[dict]:
    """Отклики перевозчиков на посылку — для экрана отправителя."""
    rows = (await session.execute(
        select(Match, Flight, User)
        .join(Flight, Match.flight_id == Flight.id)
        .join(User, Flight.traveler_id == User.id)
        .where(Match.parcel_id == parcel_id)
        .order_by(Match.created_at.desc())
    )).all()

    return [{
        "id": match.id,
        "status": match.status.value,
        "initiator": match.initiator,
        "created_at": match.created_at,
        "flight": {
            "id": flight.id,
            "from_city": flight.from_city,
            "to_city": flight.to_city,
            "flight_date": flight.flight_date,
            "available_kg": flight.available_kg,
            "price_per_kg": flight.price_per_kg,
            "status": flight.status.value,
        },
        "traveler": {
            "id": traveler.id,
            "name": traveler.full_name,
            "rating": traveler.rating,
            "reviews_count": traveler.reviews_count,
            "deliveries_count": traveler.deliveries_count,
            "is_verified": traveler.is_verified,
        },
    } for match, flight, traveler in rows]


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


async def get_incoming_requests(
    session: AsyncSession,
    traveler_id: int,
) -> list[dict]:
    """Все заявки по активным рейсам перевозчика, сгруппированные по рейсу.

    Заявки видны всегда — платный доступ ограничивает только ответ на них.
    """
    from datetime import date

    from shared.models.flight import FlightStatus

    # Берём только рейсы, которые ещё не улетели
    flights = list((await session.execute(
        select(Flight)
        .where(
            Flight.traveler_id == traveler_id,
            Flight.status == FlightStatus.ACTIVE,
            Flight.flight_date >= date.today(),
        )
        .order_by(Flight.flight_date.asc())
    )).scalars().all())

    if not flights:
        return []

    # Одним запросом достаём заявки по всем рейсам сразу
    flight_ids = [f.id for f in flights]
    rows = (await session.execute(
        select(Match, Parcel, User)
        .join(Parcel, Match.parcel_id == Parcel.id)
        .join(User, Parcel.sender_id == User.id)
        .where(
            Match.flight_id.in_(flight_ids),
            Match.status == MatchStatus.PENDING,
        )
        .order_by(Match.created_at.desc())
    )).all()

    # Раскладываем заявки по рейсам
    by_flight: dict[int, list[dict]] = {fid: [] for fid in flight_ids}
    for match, parcel, sender in rows:
        by_flight[match.flight_id].append({
            "id": match.id,
            "status": match.status.value,
            "created_at": match.created_at,
            "parcel": {
                "id": parcel.id,
                "description": parcel.description,
                "weight": parcel.weight,
                "price": parcel.price,
            },
            "sender": {
                "id": sender.id,
                "name": sender.full_name,
                "rating": sender.rating,
                "reviews_count": sender.reviews_count,
                "deliveries_count": sender.deliveries_count,
            },
        })

    return [
        {
            "flight": {
                "id": f.id,
                "from_city": f.from_city,
                "to_city": f.to_city,
                "flight_date": f.flight_date.isoformat(),
                "available_kg": f.available_kg,
                "price_per_kg": f.price_per_kg,
            },
            "requests": by_flight[f.id],
        }
        for f in flights
    ]


def _may_answer(match: Match, flight: Flight, parcel: Parcel, actor_id: int) -> bool:
    """Отвечает на заявку противоположная сторона: на заявку отправителя —
    хозяин рейса, на отклик перевозчика — хозяин посылки."""
    if match.initiator == "traveler":
        return parcel.sender_id == actor_id
    return flight.traveler_id == actor_id


async def accept_match(
    session: AsyncSession,
    match_id: int,
    actor_id: int,
) -> Match:
    """Принять заявку — привязать посылку к перевозчику."""
    traveler_id = actor_id
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
    parcel = await session.get(Parcel, match.parcel_id)
    if not flight or not parcel:
        raise ValueError("Match is broken")
    if not _may_answer(match, flight, parcel, actor_id):
        raise ValueError("Not authorized")

    # Перевозчик всегда хозяин рейса, кто бы ни нажимал «принять»
    traveler_id = flight.traveler_id

    # Отвечать на заявки можно только когда открыт сегодняшний рабочий день.
    # Отклик перевозчика день уже открыл, поэтому проверяем только заявки отправителя.
    if match.initiator != "traveler":
        traveler = await session.get(User, traveler_id)
        if traveler:
            await ensure_can_respond(session, traveler)

    # Обновляем статус заявки
    match.status = MatchStatus.ACCEPTED

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

    # Вторая сторона узнаёт о решении
    if match.initiator == "traveler":
        await notification_service.notify_offer_accepted(session, parcel, flight)
    else:
        await notification_service.notify_request_accepted(session, parcel, flight)

    # Посылку забрали — объявления в группах закрываем
    await crosspost_service.close_parcel_posts(session, parcel)

    logger.info("[MATCH] Принят: match=%s, traveler=%s", match_id, traveler_id)
    return match


async def decline_match(
    session: AsyncSession,
    match_id: int,
    actor_id: int,
) -> Match:
    """Отклонить заявку."""
    traveler_id = actor_id
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
    parcel = await session.get(Parcel, match.parcel_id)
    if not flight or not parcel:
        raise ValueError("Match is broken")
    if not _may_answer(match, flight, parcel, actor_id):
        raise ValueError("Not authorized")

    match.status = MatchStatus.DECLINED
    await session.commit()
    await session.refresh(match)

    # Второй стороне сообщаем об отказе
    if match.initiator == "traveler":
        await notification_service.notify_offer_declined(session, parcel, flight)
    else:
        await notification_service.notify_request_declined(session, parcel)

    logger.info("[MATCH] Отклонён: match=%s, traveler=%s", match_id, traveler_id)
    return match
