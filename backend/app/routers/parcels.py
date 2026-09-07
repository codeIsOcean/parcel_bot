import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.parcels import (
    DeliveryConfirmRequest, DeliveryStepRequest, OfferCreate,
    ParcelCreate, ParcelResponse, PaginatedParcels,
)
from backend.app.services import delivery_service, match_service, media_service, parcel_service
from backend.app.services.delivery_service import DeliveryError
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
    # Отправителя показываем перевозчику, который смотрит карточку из группы
    sender = await session.get(User, parcel.sender_id)
    if sender:
        response.sender_name = sender.full_name
        response.sender_rating = sender.rating
        response.sender_reviews_count = sender.reviews_count
        response.sender_verified = sender.is_verified
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

    # Отправитель выбрал конкретный рейс — заявка на него уходит сразу
    if data.flight_id:
        try:
            await match_service.create_match(session, parcel.id, data.flight_id, sender_id=user.id)
        except ValueError as e:
            # Посылка уже создана, заявку можно подать повторно с экрана рейса
            logger.warning("[PARCEL] Заявка на рейс %s не создана: %s", data.flight_id, e)

    return await _enrich_parcel_response(session, parcel)


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


@router.post("/{parcel_id}/offer", status_code=201)
async def offer_flight(
    parcel_id: int,
    data: OfferCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Перевозчик откликается на посылку своим рейсом."""
    try:
        match = await match_service.create_offer(session, parcel_id, data.flight_id, traveler_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": match.id, "status": match.status.value, "initiator": match.initiator}


@router.get("/{parcel_id}/offers")
async def get_parcel_offers(
    parcel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Отклики и заявки по посылке. Отправителю — все, перевозчику — только свои."""
    parcel = await parcel_service.get_parcel_by_id(session, parcel_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    offers = await match_service.get_parcel_offers(session, parcel_id)
    if parcel.sender_id != user.id:
        offers = [o for o in offers if o["traveler"]["id"] == user.id]
    return {"items": offers, "total": len(offers)}


@router.get("/{parcel_id}/tracking")
async def get_tracking(
    parcel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Отслеживание посылки: этапы, код выдачи и доступные действия."""
    parcel = await parcel_service.get_parcel_by_id(session, parcel_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    # Видеть отслеживание могут только участники сделки
    if user.id not in (parcel.sender_id, parcel.traveler_id):
        raise HTTPException(status_code=403, detail="Not a participant of this parcel")

    is_traveler = user.id == parcel.traveler_id
    status = parcel.status.value

    return {
        "parcel": (await _enrich_parcel_response(session, parcel)).model_dump(),
        "timeline": delivery_service.timeline(parcel),
        # Снимки по этапам — доказательство приёма и выдачи
        "photos": {
            "parcel": media_service.to_urls(parcel.photo_file_ids),
            "handover": media_service.to_urls(parcel.handover_photo_file_ids),
            "delivery": media_service.to_urls(parcel.delivery_photo_file_ids),
        },
        # Код знает только отправитель — он называет его получателю
        "handover_code": parcel.handover_code if user.id == parcel.sender_id else None,
        "is_traveler": is_traveler,
        # Что перевозчик может сделать прямо сейчас
        "actions": {
            "can_hand": is_traveler and status == "accepted",
            "can_transit": is_traveler and status == "handed",
            "can_arrive": is_traveler and status == "in_transit" and not parcel.arrived_at,
            "can_deliver": is_traveler and status == "in_transit",
        },
    }


@router.post("/{parcel_id}/handed", response_model=ParcelResponse)
async def mark_handed(
    parcel_id: int,
    data: DeliveryStepRequest | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Перевозчик забрал посылку у отправителя."""
    try:
        parcel = await delivery_service.mark_handed(
            session, parcel_id, user.id,
            photo_file_ids=data.photo_file_ids if data else None,
        )
        return await _enrich_parcel_response(session, parcel)
    except DeliveryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{parcel_id}/transit", response_model=ParcelResponse)
async def mark_in_transit(
    parcel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Перевозчик вылетел."""
    try:
        parcel = await delivery_service.mark_in_transit(session, parcel_id, user.id)
        return await _enrich_parcel_response(session, parcel)
    except DeliveryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{parcel_id}/arrived", response_model=ParcelResponse)
async def mark_arrived(
    parcel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Перевозчик прилетел в город назначения."""
    try:
        parcel = await delivery_service.mark_arrived(session, parcel_id, user.id)
        return await _enrich_parcel_response(session, parcel)
    except DeliveryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{parcel_id}/delivered", response_model=ParcelResponse)
async def mark_delivered(
    parcel_id: int,
    data: DeliveryConfirmRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Перевозчик закрывает доставку кодом получателя."""
    try:
        parcel = await delivery_service.mark_delivered(
            session, parcel_id, user.id,
            code=data.code, photo_file_ids=data.photo_file_ids,
        )
        return await _enrich_parcel_response(session, parcel)
    except DeliveryError as e:
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
