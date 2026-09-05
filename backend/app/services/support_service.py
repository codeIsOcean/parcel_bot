"""Чат пользователя с администратором сервиса.

Три входа в одну и ту же переписку: пользователь пишет из Mini App,
администратор отвечает из Telegram или из KVD Ads Panel (CRM). Сообщение
сначала ложится в базу и только потом уходит пушем и копией в CRM — так
администратор никогда не увидит того, чего нет в базе.

Копии сообщений уходят в CRM через crm_bridge (после коммита). Ответ,
пришедший ИЗ CRM (origin="crm"), обратно в CRM не зеркалится — петли нет.

У одного пользователя одновременно живёт одно активное обращение: переписка
не рассыпается на ветки, а администратор всегда отвечает в последнюю.
"""

import html
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services.crm_bridge import SENDER_OPERATOR, SENDER_USER, CrmEvent, crm_bridge
from shared.locale.notify_texts import nt
from shared.models.chat import SupportMessage, SupportSession
from shared.models.user import User
from shared.notify import fire_and_forget, send_message, webapp_button

logger = logging.getLogger(__name__)

# Роли отправителей в переписке
ROLE_USER = "user"
ROLE_ADMIN = "admin"

# Откуда пришёл ответ администратора: из бота или из CRM-панели
ORIGIN_APP = "app"
ORIGIN_CRM = "crm"


class SupportUnavailable(Exception):
    """Поддержка не настроена: не задан ни один администратор."""


def _now() -> datetime:
    """Текущее время в UTC."""
    return datetime.now(timezone.utc)


def admin_ids() -> list[int]:
    """Кому уходят обращения."""
    return settings.admin_id_list


def primary_admin_id() -> int:
    """От чьего имени пишутся ответы из CRM: первый администратор, иначе 0."""
    ids = admin_ids()
    return ids[0] if ids else 0


def is_available() -> bool:
    """Есть кому отвечать: администраторы в Telegram или CRM-панель."""
    return bool(admin_ids()) or settings.crm_enabled


def client_snapshot(user: User) -> dict:
    """Снимок карточки клиента для CRM: то, что оператор видит рядом с перепиской."""
    return {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "phone": user.phone,
        "city": user.city,
        "language": user.lang,
        "role": user.role.value if user.role else None,
        "registered_at": user.created_at.isoformat() if user.created_at else None,
        # Дополнительные строки профиля — панель показывает их как есть
        "details": [
            {"label": "Рейтинг", "value": user.rating},
            {"label": "Доставок", "value": user.deliveries_count},
            {"label": "Проверен", "value": "да" if user.is_verified else "нет"},
            {"label": "Премиум", "value": "да" if user.is_premium else "нет"},
            {"label": "Баланс ⭐", "value": user.balance_stars},
            {"label": "Заблокирован", "value": "да" if user.is_blocked else "нет"},
        ],
    }


def _mirror_to_crm(sender: str, message: SupportMessage, user: User) -> None:
    """Копия сообщения в CRM. Вызывать после коммита."""
    crm_bridge.schedule(CrmEvent(
        sender=sender,
        user_id=user.id,
        text=message.text,
        external_id=message.id,
        session_id=message.session_id,
        created_at=message.created_at,
        client=client_snapshot(user),
    ))


async def get_or_create_session(session: AsyncSession, user_id: int) -> SupportSession:
    """Активное обращение пользователя, при отсутствии — новое."""
    existing = (await session.execute(
        select(SupportSession)
        .where(SupportSession.user_id == user_id, SupportSession.is_active == True)  # noqa: E712
        .order_by(SupportSession.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if existing:
        return existing

    ticket = SupportSession(user_id=user_id, is_active=True, is_pending=True)
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    logger.info("[SUPPORT] Новое обращение %s от пользователя %s", ticket.id, user_id)
    return ticket


async def get_messages(
    session: AsyncSession, user_id: int, limit: int = 100,
) -> list[SupportMessage]:
    """История переписки пользователя с поддержкой."""
    ticket = (await session.execute(
        select(SupportSession)
        .where(SupportSession.user_id == user_id)
        .order_by(SupportSession.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not ticket:
        return []

    messages = list((await session.execute(
        select(SupportMessage)
        .where(SupportMessage.session_id == ticket.id)
        .order_by(SupportMessage.created_at.asc())
        .limit(limit)
    )).scalars().all())

    # Ответы администратора отмечаем прочитанными
    await session.execute(
        update(SupportMessage)
        .where(
            SupportMessage.session_id == ticket.id,
            SupportMessage.sender_role == ROLE_ADMIN,
            SupportMessage.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await session.commit()

    return messages


async def unread_for_user(session: AsyncSession, user_id: int) -> int:
    """Сколько ответов поддержки пользователь ещё не видел."""
    return (await session.execute(
        select(func.count(SupportMessage.id))
        .join(SupportSession, SupportMessage.session_id == SupportSession.id)
        .where(
            SupportSession.user_id == user_id,
            SupportMessage.sender_role == ROLE_ADMIN,
            SupportMessage.is_read == False,  # noqa: E712
        )
    )).scalar() or 0


async def send_user_message(
    session: AsyncSession, user: User, text: str,
) -> SupportMessage:
    """Пользователь пишет в поддержку."""
    if not is_available():
        raise SupportUnavailable()

    ticket = await get_or_create_session(session, user.id)

    message = SupportMessage(
        session_id=ticket.id,
        sender_id=user.id,
        sender_role=ROLE_USER,
        text=text,
    )
    session.add(message)

    # Обращение снова ждёт ответа
    ticket.is_pending = True
    ticket.message_count = (ticket.message_count or 0) + 1
    await session.commit()
    await session.refresh(message)

    # Пуш администраторам и копия в CRM уходят после записи в базу
    _notify_admins(user, ticket.id, text)
    _mirror_to_crm(SENDER_USER, message, user)

    logger.info("[SUPPORT] Сообщение пользователя %s в обращении %s", user.id, ticket.id)
    return message


def _notify_admins(user: User, ticket_id: int, text: str) -> None:
    """Разослать обращение администраторам."""
    # Текст пользователя экранируем: он попадает в HTML-разметку
    safe_text = html.escape(text[:800])
    username = f"@{user.username}" if user.username else f"id {user.id}"

    body = nt(
        "ru", "support_admin_push",
        ticket_id=ticket_id,
        user_name=html.escape(user.full_name),
        username=html.escape(username),
        text=safe_text,
    )

    # Кнопка сразу ставит администратора в режим ответа этому человеку
    markup = {
        "inline_keyboard": [[
            {"text": nt("ru", "btn_support_reply"), "callback_data": f"support_reply:{user.id}"},
        ]]
    }

    for admin_id in admin_ids():
        fire_and_forget(send_message(admin_id, body, reply_markup=markup))


async def send_admin_reply(
    session: AsyncSession, admin_id: int, user_id: int, text: str,
    origin: str = ORIGIN_APP,
) -> SupportMessage | None:
    """Администратор отвечает пользователю.

    origin — откуда ответ: из бота (зеркалим в CRM) или из CRM (не зеркалим).
    """
    ticket = (await session.execute(
        select(SupportSession)
        .where(SupportSession.user_id == user_id)
        .order_by(SupportSession.id.desc())
        .limit(1)
    )).scalar_one_or_none()

    # Отвечать некуда: пользователь не обращался
    if not ticket:
        return None

    message = SupportMessage(
        session_id=ticket.id,
        sender_id=admin_id,
        sender_role=ROLE_ADMIN,
        text=text,
    )
    session.add(message)

    ticket.is_pending = False
    ticket.message_count = (ticket.message_count or 0) + 1
    await session.commit()
    await session.refresh(message)

    # Пуш пользователю с кнопкой на экран поддержки
    user = await session.get(User, user_id)
    if user and not user.bot_blocked:
        body = nt(user.lang, "support_user_push", text=html.escape(text[:800]))
        fire_and_forget(send_message(
            user_id, body,
            reply_markup=webapp_button(nt(user.lang, "btn_open_support"), "/support"),
        ))
    # Ответ из бота дублируем в CRM; ответ из CRM обратно не возвращаем
    if user and origin != ORIGIN_CRM:
        _mirror_to_crm(SENDER_OPERATOR, message, user)

    logger.info("[SUPPORT] Ответ администратора %s пользователю %s", admin_id, user_id)
    return message


async def close_session(session: AsyncSession, user_id: int) -> bool:
    """Закрыть обращение."""
    ticket = (await session.execute(
        select(SupportSession)
        .where(SupportSession.user_id == user_id, SupportSession.is_active == True)  # noqa: E712
        .order_by(SupportSession.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if not ticket:
        return False

    ticket.is_active = False
    ticket.is_pending = False
    ticket.closed_at = _now()
    await session.commit()
    return True


async def pending_sessions(session: AsyncSession, limit: int = 20) -> list[SupportSession]:
    """Обращения, которые ждут ответа. Нужны администратору в боте."""
    return list((await session.execute(
        select(SupportSession)
        .where(SupportSession.is_pending == True, SupportSession.is_active == True)  # noqa: E712
        .order_by(SupportSession.updated_at.asc())
        .limit(limit)
    )).scalars().all())
