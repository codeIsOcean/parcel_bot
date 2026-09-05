import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.chats import (
    ChatPreview, MessageResponse, MessageSend, PriceOffer,
)
from backend.app.services import chat_service, notification_service
from backend.app.services.access_service import ensure_can_write
from shared.models.message import RelayMessage
from shared.models.parcel import Parcel
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["chats"])


class ChatStart(BaseModel):
    """Открытие переписки по посылке."""
    parcel_id: int


@router.get("", response_model=list[ChatPreview])
async def get_my_chats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Список моих переписок с превью."""
    items = await chat_service.list_user_chats(session, user.id)
    return [ChatPreview(**item) for item in items]


@router.post("/start")
async def start_chat(
    data: ChatStart,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Открыть переписку по посылке.

    Доступно обеим сторонам сделки. Если переписка уже есть, возвращаем её —
    один чат на посылку.
    """
    parcel = await session.get(Parcel, data.parcel_id)
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    # Собеседника определяем по посылке, а не по запросу клиента
    if user.id == parcel.sender_id:
        traveler_id = parcel.traveler_id
        if not traveler_id:
            raise HTTPException(status_code=400, detail="Parcel has no traveler yet")
    elif user.id == parcel.traveler_id:
        traveler_id = parcel.traveler_id
    else:
        raise HTTPException(status_code=403, detail="Not a participant of this parcel")

    chat = await chat_service.ensure_session(session, parcel, traveler_id)
    return {"chat_id": chat.id, "parcel_id": chat.parcel_id}


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Сообщения переписки."""
    chat = await chat_service.get_session_for_user(session, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = list((await session.execute(
        select(RelayMessage)
        .where(RelayMessage.chat_id == chat_id)
        .order_by(RelayMessage.created_at.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    )).scalars().all())

    # Помечаем входящие прочитанными одним запросом
    await session.execute(
        update(RelayMessage)
        .where(and_(
            RelayMessage.chat_id == chat_id,
            RelayMessage.receiver_id == user.id,
            RelayMessage.is_read == False,  # noqa: E712
        ))
        .values(is_read=True)
    )
    await session.commit()

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    chat_id: int,
    data: MessageSend,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Отправить сообщение в переписку."""
    chat = await chat_service.get_session_for_user(session, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Перевозчик пишет отправителю только по оплаченной публикации
    await ensure_can_write(session, user, chat.parcel_id)

    message = await chat_service.add_message(session, chat, user.id, data.text)

    # Собеседник получает пуш, даже если Mini App закрыт
    await notification_service.notify_new_message(
        session, message.receiver_id, user.full_name, data.text, chat_id,
    )

    logger.info("[RELAY] Сообщение: chat=%s, from=%s", chat_id, user.id)
    return MessageResponse.model_validate(message)


@router.post("/{chat_id}/offer", response_model=MessageResponse, status_code=201)
async def offer_price(
    chat_id: int,
    data: PriceOffer,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Предложить цену (торг)."""
    chat = await chat_service.get_session_for_user(session, chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Торг — это тоже ответ на заявку, требует оплаченной публикации
    await ensure_can_write(session, user, chat.parcel_id)

    text = f"💰 Предложение: ${data.price}"
    message = await chat_service.add_message(
        session, chat, user.id, text, message_type="offer", offer_price=data.price,
    )

    await notification_service.notify_new_message(
        session, message.receiver_id, user.full_name, text, chat_id,
    )

    logger.info("[RELAY] Предложение цены: chat=%s, from=%s, price=%s", chat_id, user.id, data.price)
    return MessageResponse.model_validate(message)
