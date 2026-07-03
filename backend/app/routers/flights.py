import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.flights import FlightCreate, FlightResponse, PaginatedFlights
from backend.app.services import flight_service
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flights", tags=["flights"])


@router.post("", response_model=FlightResponse, status_code=201)
async def create_flight(
    data: FlightCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Опубликовать новый рейс."""
    flight = await flight_service.create_flight(
        session,
        traveler_id=user.id,
        from_city=data.from_city,
        to_city=data.to_city,
        flight_date=data.flight_date,
        available_kg=data.available_kg,
        price_per_kg=data.price_per_kg,
        flight_number=data.flight_number,
        notes=data.notes,
    )
    # Добавляем данные перевозчика в ответ
    return FlightResponse(
        **{k: getattr(flight, k) for k in FlightResponse.model_fields if hasattr(flight, k)},
        traveler_name=user.full_name,
        traveler_rating=user.rating,
        traveler_trips=user.deliveries_count,
        traveler_verified=user.is_verified,
    )


@router.get("", response_model=PaginatedFlights)
async def search_flights(
    from_city: str | None = Query(None, alias="from"),
    to_city: str | None = Query(None, alias="to"),
    min_kg: float | None = Query(None),
    sort: str = Query("date", description="date / price / kg / rating", pattern="^(date|price|kg|rating)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Поиск рейсов (попутчиков) по маршруту."""
    flights, total = await flight_service.search_flights(
        session,
        from_city=from_city,
        to_city=to_city,
        min_kg=min_kg,
        sort=sort,
        page=page,
        limit=limit,
    )
    return PaginatedFlights(
        items=[FlightResponse(**f) for f in flights],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/my", response_model=PaginatedFlights)
async def get_my_flights(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить мои рейсы (для перевозчика)."""
    flights, total = await flight_service.get_user_flights(
        session, user.id, page=page, limit=limit,
    )
    # Добавляем данные перевозчика к своим рейсам
    items = []
    for f in flights:
        items.append(FlightResponse(
            **{k: getattr(f, k) for k in FlightResponse.model_fields if hasattr(f, k)},
            traveler_name=user.full_name,
            traveler_rating=user.rating,
            traveler_trips=user.deliveries_count,
            traveler_verified=user.is_verified,
        ))
    return PaginatedFlights(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{flight_id}", response_model=FlightResponse)
async def get_flight_detail(
    flight_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Получить детали рейса по ID."""
    from sqlalchemy import select
    from shared.models.flight import Flight

    result = await session.execute(select(Flight).where(Flight.id == flight_id))
    flight = result.scalar_one_or_none()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # Загружаем данные перевозчика
    traveler = await session.get(User, flight.traveler_id)
    return FlightResponse(
        **{k: getattr(flight, k) for k in FlightResponse.model_fields if hasattr(flight, k)},
        traveler_name=traveler.full_name if traveler else None,
        traveler_rating=traveler.rating if traveler else None,
        traveler_trips=traveler.deliveries_count if traveler else None,
        traveler_verified=traveler.is_verified if traveler else None,
    )
