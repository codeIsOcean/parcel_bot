import logging
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from shared.models.flight import Flight, FlightStatus
from shared.models.user import User

logger = logging.getLogger(__name__)


async def create_flight(
    session: AsyncSession,
    traveler_id: int,
    from_city: str,
    to_city: str,
    flight_date: date,
    available_kg: float,
    price_per_kg: float,
    flight_number: str | None = None,
    notes: str | None = None,
) -> Flight:
    """Опубликовать новый рейс."""
    logger.info(
        "[FLIGHT] Создание: traveler=%s, route=%s→%s, date=%s, kg=%s",
        traveler_id, from_city, to_city, flight_date, available_kg,
    )

    # Создаём запись
    flight = Flight(
        traveler_id=traveler_id,
        from_city=from_city,
        to_city=to_city,
        flight_date=flight_date,
        flight_number=flight_number,
        available_kg=available_kg,
        total_kg=available_kg,
        price_per_kg=price_per_kg,
        notes=notes,
        status=FlightStatus.ACTIVE,
    )
    session.add(flight)
    await session.commit()
    await session.refresh(flight)

    logger.info("[FLIGHT] Создан: flight_id=%s", flight.id)
    return flight


async def search_flights(
    session: AsyncSession,
    from_city: str | None = None,
    to_city: str | None = None,
    min_kg: float | None = None,
    sort: str = "date",
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """Поиск активных рейсов с данными перевозчика."""
    # Базовый запрос — только активные рейсы
    query = select(Flight, User).join(User, Flight.traveler_id == User.id)
    query = query.where(Flight.status == FlightStatus.ACTIVE)
    query = query.where(Flight.flight_date >= date.today())

    # Фильтры
    if from_city:
        query = query.where(Flight.from_city == from_city)
    if to_city:
        query = query.where(Flight.to_city == to_city)
    if min_kg:
        query = query.where(Flight.available_kg >= min_kg)

    # Считаем общее количество (используем отдельный запрос только по Flight.id)
    count_base = select(func.count(Flight.id)).join(User, Flight.traveler_id == User.id)
    count_base = count_base.where(Flight.status == FlightStatus.ACTIVE)
    count_base = count_base.where(Flight.flight_date >= date.today())
    if from_city:
        count_base = count_base.where(Flight.from_city == from_city)
    if to_city:
        count_base = count_base.where(Flight.to_city == to_city)
    if min_kg:
        count_base = count_base.where(Flight.available_kg >= min_kg)
    total = (await session.execute(count_base)).scalar() or 0

    # Сортировка
    if sort == "price":
        query = query.order_by(Flight.price_per_kg.asc())
    elif sort == "kg":
        query = query.order_by(Flight.available_kg.desc())
    elif sort == "rating":
        query = query.order_by(User.rating.desc())
    else:
        query = query.order_by(Flight.flight_date.asc())

    # Пагинация
    query = query.offset((page - 1) * limit).limit(limit)

    result = await session.execute(query)
    rows = result.all()

    # Формируем ответ с данными перевозчика
    flights = []
    for flight, user in rows:
        flights.append({
            "id": flight.id,
            "traveler_id": flight.traveler_id,
            "from_city": flight.from_city,
            "to_city": flight.to_city,
            "flight_date": flight.flight_date,
            "flight_number": flight.flight_number,
            "available_kg": flight.available_kg,
            "total_kg": flight.total_kg,
            "price_per_kg": flight.price_per_kg,
            "notes": flight.notes,
            "status": flight.status.value,
            "requests_count": flight.requests_count,
            "created_at": flight.created_at,
            "traveler_name": user.full_name,
            "traveler_rating": user.rating,
            "traveler_trips": user.deliveries_count,
            "traveler_verified": user.is_verified,
        })

    return flights, total


async def get_user_flights(
    session: AsyncSession,
    user_id: int,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Flight], int]:
    """Получить рейсы перевозчика."""
    query = select(Flight).where(Flight.traveler_id == user_id)
    query = query.order_by(Flight.flight_date.desc())

    # Считаем количество
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    # Пагинация
    query = query.offset((page - 1) * limit).limit(limit)
    result = await session.execute(query)
    flights = list(result.scalars().all())

    return flights, total
