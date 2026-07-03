import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import match_service
from shared.models.user import User


class MatchCreate(BaseModel):
    """Создание заявки."""
    parcel_id: int
    flight_id: int

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", status_code=201)
async def create_match(
    data: MatchCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Создать заявку — связать посылку с рейсом."""
    try:
        match = await match_service.create_match(
            session, data.parcel_id, data.flight_id, sender_id=user.id,
        )
        return {"id": match.id, "status": match.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flight/{flight_id}")
async def get_flight_requests(
    flight_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Получить заявки на рейс (только владелец рейса)."""
    # Проверяем что рейс принадлежит текущему пользователю
    from shared.models.flight import Flight
    from sqlalchemy import select
    flight = (await session.execute(
        select(Flight).where(Flight.id == flight_id)
    )).scalar_one_or_none()
    if not flight or flight.traveler_id != user.id:
        raise HTTPException(status_code=403, detail="Not your flight")

    requests, total = await match_service.get_flight_requests(session, flight_id, page, limit)
    return {"items": requests, "total": total, "page": page, "limit": limit}


@router.post("/{match_id}/accept")
async def accept_match(
    match_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Принять заявку на перевозку."""
    try:
        match = await match_service.accept_match(session, match_id, user.id)
        return {"id": match.id, "status": match.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{match_id}/decline")
async def decline_match(
    match_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Отклонить заявку на перевозку."""
    try:
        match = await match_service.decline_match(session, match_id, user.id)
        return {"id": match.id, "status": match.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
