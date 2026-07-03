import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.parcels import ParcelCreate, ParcelResponse, PaginatedParcels
from backend.app.services import parcel_service
from shared.models.user import User

logger = logging.getLogger(__name__)


async def _enrich_parcel_response(session: AsyncSession, parcel) -> ParcelResponse:
    """Обогащаем ответ данными перевозчика."""
    response = ParcelResponse.model_validate(parcel)
    if parcel.traveler_id:
        traveler = await session.get(User, parcel.traveler_id)
        if traveler:
            response.traveler_name = traveler.full_name
            response.traveler_rating = traveler.rating
    return response

router = APIRouter(prefix="/parcels", tags=["parcels"])


@router.post("", response_model=ParcelResponse, status_code=201)
async def create_parcel(
    data: ParcelCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Создать новую посылку (заявку на отправку)."""
    parcel = await parcel_service.create_parcel(
        session,
        sender_id=user.id,
        from_city=data.from_city,
        to_city=data.to_city,
        description=data.description,
        weight=data.weight,
        size=data.size,
        price=data.price,
        traveler_id=data.traveler_id,
    )
    return ParcelResponse.model_validate(parcel)


@router.get("/my", response_model=PaginatedParcels)
async def get_my_parcels(
    status: str | None = Query(None, description="active / completed / pending"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить мои посылки с пагинацией."""
    parcels, total = await parcel_service.get_user_parcels(
        session, user.id, status=status, page=page, limit=limit,
    )
    return PaginatedParcels(
        items=[ParcelResponse.model_validate(p) for p in parcels],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{parcel_id}", response_model=ParcelResponse)
async def get_parcel(
    parcel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить детали посылки."""
    parcel = await parcel_service.get_parcel_by_id(session, parcel_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return await _enrich_parcel_response(session, parcel)


@router.post("/{parcel_id}/status", response_model=ParcelResponse)
async def update_parcel_status(
    parcel_id: int,
    new_status: str = Query(..., description="handed / in_transit / delivered"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Обновить статус посылки (accepted→handed→in_transit→delivered)."""
    try:
        parcel = await parcel_service.update_parcel_status(
            session, parcel_id, new_status, actor_id=user.id,
        )
        return await _enrich_parcel_response(session, parcel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{parcel_id}/cancel", response_model=ParcelResponse)
async def cancel_parcel(
    parcel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Отменить посылку."""
    parcel = await parcel_service.cancel_parcel(session, parcel_id, user.id)
    if not parcel:
        raise HTTPException(status_code=400, detail="Cannot cancel this parcel")
    return ParcelResponse.model_validate(parcel)
