"""Тесты переписки с поддержкой и чата участников сделки."""

from datetime import date, timedelta

import pytest

from backend.app.config import settings
from backend.app.services import chat_service, support_service
from backend.app.services.support_service import SupportUnavailable
from shared.models.flight import Flight, FlightStatus
from shared.models.parcel import Parcel, ParcelSize, ParcelStatus
from shared.models.user import User

USER_ID = 1
TRAVELER_ID = 2
ADMIN_ID = 777


@pytest.fixture(autouse=True)
def with_admin(monkeypatch):
    """Поддержка настроена: администратор задан."""
    monkeypatch.setattr(settings, "admin_ids", str(ADMIN_ID))


async def add_users(session) -> tuple[User, User]:
    """Отправитель и перевозчик."""
    sender = User(id=USER_ID, first_name="Отправитель", lang="ru")
    traveler = User(id=TRAVELER_ID, first_name="Перевозчик", lang="ru")
    session.add_all([sender, traveler])
    await session.commit()
    return sender, traveler


async def add_parcel(session) -> Parcel:
    """Посылка отправителя."""
    parcel = Parcel(
        sender_id=USER_ID, from_city="Dubai", to_city="Almaty",
        description="Документы", weight=2.0, size=ParcelSize.SMALL,
        price=25.0, status=ParcelStatus.PENDING,
    )
    session.add(parcel)
    await session.commit()
    await session.refresh(parcel)
    return parcel


@pytest.mark.asyncio
async def test_support_requires_admin(session, monkeypatch):
    """Без администраторов писать в поддержку некому."""
    monkeypatch.setattr(settings, "admin_ids", "")
    sender, _ = await add_users(session)

    with pytest.raises(SupportUnavailable):
        await support_service.send_user_message(session, sender, "Вопрос")


@pytest.mark.asyncio
async def test_support_creates_one_session(session):
    """Два сообщения подряд попадают в одно обращение."""
    sender, _ = await add_users(session)

    await support_service.send_user_message(session, sender, "Первый вопрос")
    await support_service.send_user_message(session, sender, "Второй вопрос")

    messages = await support_service.get_messages(session, sender.id)
    assert len(messages) == 2
    assert len({m.session_id for m in messages}) == 1


@pytest.mark.asyncio
async def test_admin_reply_lands_in_same_thread(session):
    """Ответ администратора виден пользователю в той же переписке."""
    sender, _ = await add_users(session)
    await support_service.send_user_message(session, sender, "Вопрос")

    reply = await support_service.send_admin_reply(session, ADMIN_ID, sender.id, "Ответ")
    assert reply is not None

    messages = await support_service.get_messages(session, sender.id)
    assert [m.sender_role for m in messages] == ["user", "admin"]


@pytest.mark.asyncio
async def test_admin_reply_without_ticket(session):
    """Ответить пользователю без обращения нельзя."""
    await add_users(session)
    assert await support_service.send_admin_reply(session, ADMIN_ID, USER_ID, "Ответ") is None


@pytest.mark.asyncio
async def test_pending_queue(session):
    """Новое обращение попадает в очередь, ответ его оттуда убирает."""
    sender, _ = await add_users(session)
    await support_service.send_user_message(session, sender, "Вопрос")

    assert len(await support_service.pending_sessions(session)) == 1

    await support_service.send_admin_reply(session, ADMIN_ID, sender.id, "Ответ")
    assert await support_service.pending_sessions(session) == []


@pytest.mark.asyncio
async def test_chat_session_created_once(session):
    """Переписка по посылке создаётся один раз."""
    await add_users(session)
    parcel = await add_parcel(session)

    first = await chat_service.ensure_session(session, parcel, TRAVELER_ID)
    second = await chat_service.ensure_session(session, parcel, TRAVELER_ID)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_chat_participants_only(session):
    """Посторонний переписку не откроет."""
    await add_users(session)
    parcel = await add_parcel(session)
    chat = await chat_service.ensure_session(session, parcel, TRAVELER_ID)

    assert await chat_service.get_session_for_user(session, chat.id, USER_ID) is not None
    assert await chat_service.get_session_for_user(session, chat.id, 999) is None


@pytest.mark.asyncio
async def test_chat_message_addresses_other_side(session):
    """Получатель сообщения определяется по сессии, а не по запросу."""
    await add_users(session)
    parcel = await add_parcel(session)
    chat = await chat_service.ensure_session(session, parcel, TRAVELER_ID)

    message = await chat_service.add_message(session, chat, USER_ID, "Привет")
    assert message.receiver_id == TRAVELER_ID

    await session.refresh(chat)
    assert chat.message_count == 1


@pytest.mark.asyncio
async def test_chat_list_shows_partner(session):
    """В списке переписок виден собеседник и последнее сообщение."""
    await add_users(session)
    parcel = await add_parcel(session)
    chat = await chat_service.ensure_session(session, parcel, TRAVELER_ID)
    await chat_service.add_message(session, chat, TRAVELER_ID, "Возьму")

    chats = await chat_service.list_user_chats(session, USER_ID)
    assert len(chats) == 1
    assert chats[0]["partner_id"] == TRAVELER_ID
    assert chats[0]["last_message"] == "Возьму"
    assert chats[0]["unread_count"] == 1
