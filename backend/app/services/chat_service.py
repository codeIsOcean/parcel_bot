"""Переписка между отправителем и перевозчиком.

Раньше чат существовал только как поток сообщений: собеседник вычислялся из
уже существующей переписки, поэтому начать новый чат было нельзя вообще.
Теперь участники заданы явно сессией, которая заводится в момент отклика на
рейс, и до первого сообщения чат уже существует.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.chat import ChatSession
from shared.models.flight import Flight
from shared.models.message import RelayMessage
from shared.models.parcel import Parcel
from shared.models.user import User

logger = logging.getLogger(__name__)


async def ensure_session(
    session: AsyncSession, parcel: Parcel, traveler_id: int,
) -> ChatSession:
    """Найти или создать переписку по посылке."""
    existing = (await session.execute(
        select(ChatSession).where(ChatSession.parcel_id == parcel.id)
    )).scalar_one_or_none()
    if existing:
        return existing

    chat = ChatSession(
        parcel_id=parcel.id,
        sender_id=parcel.sender_id,
        traveler_id=traveler_id,
        is_active=True,
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)

    logger.info("[CHAT] Создана переписка %s по посылке %s", chat.id, parcel.id)
    return chat


async def ensure_session_for_match(
    session: AsyncSession, parcel: Parcel, flight: Flight,
) -> ChatSession:
    """Завести переписку при отклике на рейс."""
    return await ensure_session(session, parcel, flight.traveler_id)


async def get_session_for_user(
    session: AsyncSession, chat_id: int, user_id: int,
) -> ChatSession | None:
    """Переписка, если пользователь в ней участвует."""
    chat = await session.get(ChatSession, chat_id)
    if not chat:
        return None
    # Посторонним переписку не отдаём
    if user_id not in (chat.sender_id, chat.traveler_id):
        return None
    return chat


async def list_user_chats(session: AsyncSession, user_id: int) -> list[dict]:
    """Список переписок пользователя с последним сообщением и непрочитанными."""
    chats = list((await session.execute(
        select(ChatSession)
        .where(
            (ChatSession.sender_id == user_id) | (ChatSession.traveler_id == user_id)
        )
        .order_by(ChatSession.updated_at.desc())
    )).scalars().all())

    if not chats:
        return []

    chat_ids = [c.id for c in chats]

    # Последнее сообщение в каждой переписке — одним запросом
    latest = (
        select(RelayMessage.chat_id, func.max(RelayMessage.id).label("max_id"))
        .where(RelayMessage.chat_id.in_(chat_ids))
        .group_by(RelayMessage.chat_id)
        .subquery()
    )
    last_messages = {
        m.chat_id: m
        for m in (await session.execute(
            select(RelayMessage).join(latest, RelayMessage.id == latest.c.max_id)
        )).scalars().all()
    }

    # Непрочитанные — тоже одним запросом
    unread_rows = (await session.execute(
        select(RelayMessage.chat_id, func.count().label("cnt"))
        .where(
            RelayMessage.chat_id.in_(chat_ids),
            RelayMessage.receiver_id == user_id,
            RelayMessage.is_read == False,  # noqa: E712
        )
        .group_by(RelayMessage.chat_id)
    )).all()
    unread = {row.chat_id: row.cnt for row in unread_rows}

    # Собеседники — одним запросом
    partner_ids = {c.other_side(user_id) for c in chats}
    partners = {
        u.id: u
        for u in (await session.execute(
            select(User).where(User.id.in_([p for p in partner_ids if p]))
        )).scalars().all()
    }

    result = []
    for chat in chats:
        partner_id = chat.other_side(user_id)
        partner = partners.get(partner_id)
        message = last_messages.get(chat.id)

        result.append({
            "chat_id": chat.id,
            "partner_id": partner_id,
            "partner_name": partner.full_name if partner else "—",
            "partner_avatar": partner.avatar_file_id if partner else None,
            "last_message": message.text if message else None,
            "last_message_time": message.created_at if message else chat.created_at,
            "unread_count": unread.get(chat.id, 0),
            "parcel_id": chat.parcel_id,
        })

    # Свежие переписки сверху
    result.sort(
        key=lambda c: c["last_message_time"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return result


async def add_message(
    session: AsyncSession,
    chat: ChatSession,
    sender_id: int,
    text: str,
    message_type: str = "text",
    offer_price: float | None = None,
) -> RelayMessage:
    """Записать сообщение в переписку."""
    receiver_id = chat.other_side(sender_id)

    message = RelayMessage(
        chat_id=chat.id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        text=text,
        message_type=message_type,
        offer_price=offer_price,
        parcel_id=chat.parcel_id,
    )
    session.add(message)

    # Счётчик нужен, чтобы отличать живые переписки от пустых
    chat.message_count = (chat.message_count or 0) + 1

    await session.commit()
    await session.refresh(message)
    return message
