import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import media_service
from backend.app.services.media_service import MediaError
from shared.models.parcel import Parcel
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])

# К какому этапу относится снимок
STEP_FIELDS = {
    "parcel": "photo_file_ids",
    "handover": "handover_photo_file_ids",
    "delivery": "delivery_photo_file_ids",
}


@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Загрузить фотографию и получить её адрес.

    Отдельный шаг: сначала файл, потом его адрес подставляется в посылку.
    Так работает и создание посылки, и отметка этапов доставки.
    """
    try:
        media_service.check_upload_quota(user.id)
        content = await media_service.read_limited(file)
        path = media_service.save_bytes(content, file.content_type or "", subdir="parcels")
    except MediaError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"path": path, "url": media_service.public_url(path)}


@router.post("/parcels/{parcel_id}/photos")
async def attach_parcel_photo(
    parcel_id: int,
    step: str = Query("parcel", description="parcel / handover / delivery"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Прикрепить фотографию к посылке на нужном этапе."""
    field = STEP_FIELDS.get(step)
    if not field:
        raise HTTPException(status_code=400, detail="unknown_step")

    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    # Прикреплять снимки могут только участники сделки
    if user.id not in (parcel.sender_id, parcel.traveler_id):
        raise HTTPException(status_code=403, detail="Not a participant of this parcel")

    # Снимок посылки делает отправитель, снимки этапов — перевозчик
    if step == "parcel" and user.id != parcel.sender_id:
        raise HTTPException(status_code=403, detail="Only sender can attach parcel photo")
    if step in ("handover", "delivery") and user.id != parcel.traveler_id:
        raise HTTPException(status_code=403, detail="Only traveler can attach this photo")

    try:
        media_service.check_upload_quota(user.id)
        content = await media_service.read_limited(file)
        path = media_service.save_bytes(content, file.content_type or "", subdir=f"parcels/{step}")
    except MediaError as e:
        raise HTTPException(status_code=400, detail=str(e))

    setattr(parcel, field, media_service.merge_paths(getattr(parcel, field), [path]))
    await session.commit()

    logger.info("[MEDIA] Фото к посылке %s, этап %s", parcel_id, step)
    return {
        "path": path,
        "url": media_service.public_url(path),
        "photos": media_service.to_urls(getattr(parcel, field)),
    }
