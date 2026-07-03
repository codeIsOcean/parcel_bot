import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.chats import (
    ChatPreview, MessageResponse, MessageSend, PriceOffer,
)
from shared.models.message import RelayMessage
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatPreview])
async def get_my_chats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить список моих чатов с превью."""
    # Находим все уникальные chat_id где пользователь участвует
    chat_ids_q = (
        select(RelayMessage.chat_id)
        .where(or_(
            RelayMessage.sender_id == user.id,
            RelayMessage.receiver_id == user.id,
        ))
        .distinct()
    )
    result = await session.execute(chat_ids_q)
    chat_ids = [row[0] for row in result.all()]

    if not chat_ids:
        return []

    # Загружаем последние сообщения + непрочитанные одним запросом на chat_id
    # Подзапрос: последнее сообщение в каждом чате
    from sqlalchemy.orm import aliased
    latest_subq = (
        select(
            RelayMessage.chat_id,
            func.max(RelayMessage.id).label("max_id"),
        )
        .where(RelayMessage.chat_id.in_(chat_ids))
        .group_by(RelayMessage.chat_id)
        .subquery()
    )

    # Получаем последние сообщения
    last_msgs_q = (
        select(RelayMessage)
        .join(latest_subq, RelayMessage.id == latest_subq.c.max_id)
    )
    last_msgs_result = await session.execute(last_msgs_q)
    last_msgs = {m.chat_id: m for m in last_msgs_result.scalars().all()}

    # Непрочитанные — одним запросом для всех чатов
    unread_q = (
        select(RelayMessage.chat_id, func.count().label("cnt"))
        .where(and_(
            RelayMessage.chat_id.in_(chat_ids),
            RelayMessage.receiver_id == user.id,
            RelayMessage.is_read == False,
        ))
        .group_by(RelayMessage.chat_id)
    )
    unread_result = await session.execute(unread_q)
    unread_map = {row.chat_id: row.cnt for row in unread_result.all()}

    # Собираем ID партнёров
    partner_ids = set()
    for chat_id in chat_ids:
        msg = last_msgs.get(chat_id)
        if msg:
            partner_ids.add(
                msg.receiver_id if msg.sender_id == user.id else msg.sender_id
            )

    # Загружаем партнёров одним запросом
    partners = {}
    if partner_ids:
        p_result = await session.execute(
            select(User).where(User.id.in_(partner_ids))
        )
        partners = {u.id: u for u in p_result.scalars().all()}

    # Формируем ответ
    chats = []
    for chat_id in chat_ids:
        msg = last_msgs.get(chat_id)
        if not msg:
            continue

        partner_id = msg.receiver_id if msg.sender_id == user.id else msg.sender_id
        partner = partners.get(partner_id)

        chats.append(ChatPreview(
            chat_id=chat_id,
            partner_id=partner_id,
            partner_name=partner.full_name if partner else "Unknown",
            partner_avatar=partner.avatar_file_id if partner else None,
            last_message=msg.text,
            last_message_time=msg.created_at,
            unread_count=unread_map.get(chat_id, 0),
            parcel_id=msg.parcel_id,
        ))

    # Сортируем по времени последнего сообщения
    # Сортировка по времени последнего сообщения (None — в конец)
    # Сортировка по времени последнего сообщения (None — в конец, aware datetime)
    chats.sort(key=lambda c: c.last_message_time or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return chats


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить сообщения чата."""
    # Проверяем что пользователь участвует в чате
    check_q = select(RelayMessage).where(
        and_(
            RelayMessage.chat_id == chat_id,
            or_(RelayMessage.sender_id == user.id, RelayMessage.receiver_id == user.id),
        )
    ).limit(1)
    check = (await session.execute(check_q)).scalar_one_or_none()
    if not check:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Загружаем сообщения
    query = (
        select(RelayMessage)
        .where(RelayMessage.chat_id == chat_id)
        .order_by(RelayMessage.created_at.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await session.execute(query)
    messages = result.scalars().all()

    # Помечаем как прочитанные — одним batch UPDATE
    await session.execute(
        update(RelayMessage)
        .where(and_(
            RelayMessage.chat_id == chat_id,
            RelayMessage.receiver_id == user.id,
            RelayMessage.is_read == False,
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
    """Отправить сообщение в чат."""
    # Определяем получателя из существующих сообщений
    existing_q = select(RelayMessage).where(
        and_(
            RelayMessage.chat_id == chat_id,
            or_(RelayMessage.sender_id == user.id, RelayMessage.receiver_id == user.id),
        )
    ).limit(1)
    existing = (await session.execute(existing_q)).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Определяем receiver_id
    receiver_id = (
        existing.receiver_id if existing.sender_id == user.id
        else existing.sender_id
    )

    logger.info("[RELAY] Сообщение: chat=%s, from=%s, to=%s", chat_id, user.id, receiver_id)

    # Создаём сообщение
    message = RelayMessage(
        chat_id=chat_id,
        sender_id=user.id,
        receiver_id=receiver_id,
        text=data.text,
        message_type="text",
        parcel_id=existing.parcel_id,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    return MessageResponse.model_validate(message)


@router.post("/{chat_id}/offer", response_model=MessageResponse, status_code=201)
async def offer_price(
    chat_id: int,
    data: PriceOffer,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Предложить цену (торг)."""
    # Определяем получателя
    existing_q = select(RelayMessage).where(
        and_(
            RelayMessage.chat_id == chat_id,
            or_(RelayMessage.sender_id == user.id, RelayMessage.receiver_id == user.id),
        )
    ).limit(1)
    existing = (await session.execute(existing_q)).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Chat not found")

    receiver_id = (
        existing.receiver_id if existing.sender_id == user.id
        else existing.sender_id
    )

    logger.info("[RELAY] Предложение цены: chat=%s, from=%s, price=%s", chat_id, user.id, data.price)

    # Создаём сообщение-предложение
    message = RelayMessage(
        chat_id=chat_id,
        sender_id=user.id,
        receiver_id=receiver_id,
        text=f"💰 Предложение: ${data.price}",
        message_type="offer",
        offer_price=data.price,
        parcel_id=existing.parcel_id,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    return MessageResponse.model_validate(message)
