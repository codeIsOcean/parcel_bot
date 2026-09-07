"""Кросс-постинг в телеграм-группы и реестр подключённых групп.

Решает холодный старт. Перевозчику невыгодно постить в пустое приложение,
поэтому приложение само разносит объявления по профильным чатам:
рейс («лечу, есть место») и посылку («нужно отправить») — один раз
заполнил карточку, объявление ушло всюду, а отклики вернулись внутрь
сервиса, где есть рейтинг, статусы и история.

Под каждым объявлением — кнопка-ссылка в Mini App на эту самую карточку.
В группах web_app-кнопки запрещены, поэтому ссылка вида
`https://t.me/<bot>?startapp=parcel_12`.

Опубликованные сообщения запоминаем (GroupPost): когда посылку забрали
или рейс закрыт, пост редактируется — кнопка снимается, ставится «Закрыто».
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from shared import deeplinks
from shared.locale.notify_texts import nt
from shared.models.flight import Flight
from shared.models.parcel import Parcel
from shared.models.promo_chat import GroupPost, PromoChat
from shared.models.user import User
from shared.notify import call_api, edit_message_text, fire_and_forget, send_message_id

logger = logging.getLogger(__name__)

# Виды объявлений
KIND_PARCEL = "parcel"
KIND_FLIGHT = "flight"

# Типы чатов, куда можно постить
GROUP_CHAT_TYPES = {"group", "supergroup", "channel"}

# Статусы членства, при которых бот в чате
MEMBER_STATUSES = {"member", "administrator", "creator", "restricted"}


# === Ссылки и разметка ===

def _deep_link(start_param: str) -> str | None:
    """Ссылка, открывающая Mini App с параметром запуска."""
    return deeplinks.startapp_url(settings.bot_username, start_param)


def _markup(button_text: str, start_param: str) -> dict | None:
    """Кнопка под объявлением, ведущая в приложение на нужную карточку."""
    url = _deep_link(start_param)
    if not url:
        return None
    return {"inline_keyboard": [[{"text": button_text, "url": url}]]}


def _rating(user: User) -> str:
    """Рейтинг в объявлении — главное отличие от обычного поста в чате."""
    return f"⭐ {user.rating:.1f} ({user.reviews_count})" if user.reviews_count else ""


def flight_text(flight: Flight, traveler: User) -> str:
    """Текст объявления о рейсе."""
    return nt(
        "ru", "crosspost_flight",
        from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
        available_kg=flight.available_kg, price_per_kg=flight.price_per_kg,
        traveler_name=traveler.full_name, traveler_rating=_rating(traveler),
    )


def parcel_text(parcel: Parcel, sender: User) -> str:
    """Текст объявления о посылке."""
    return nt(
        "ru", "crosspost_parcel",
        from_city=parcel.from_city, to_city=parcel.to_city,
        description=parcel.description[:300],
        weight=parcel.weight, price=parcel.price,
        sender_name=sender.full_name, sender_rating=_rating(sender),
    )


# === Выбор чатов ===

async def get_target_chats(
    session: AsyncSession, from_city: str, to_city: str, kind: str,
) -> list[PromoChat]:
    """Чаты, которым подходит маршрут и которые принимают этот вид объявлений."""
    chats = list((await session.execute(
        select(PromoChat).where(PromoChat.is_active == True)  # noqa: E712
    )).scalars().all())

    result = []
    for chat in chats:
        # Бота выгнали — слать некуда, ждём, пока админ разберётся
        if not chat.is_member:
            continue
        # Чат может принимать только рейсы или только посылки
        if kind == KIND_PARCEL and not chat.post_parcels:
            continue
        if kind == KIND_FLIGHT and not chat.post_flights:
            continue
        # Фильтр по городам задаётся на самом чате
        if chat.matches_route(from_city, to_city):
            result.append(chat)
    return result


# === Публикация ===

async def _post_and_remember(chat_id: int, kind: str, entity_id: int, text: str, markup: dict | None) -> None:
    """Фон: отправить пост и записать его message_id в своей сессии.

    Сессия запроса к этому моменту уже закрыта, поэтому открываем свою.
    """
    message_id = await send_message_id(chat_id, text, reply_markup=markup)
    if not message_id:
        return

    from backend.app.database import async_session

    try:
        async with async_session() as session:
            session.add(GroupPost(chat_id=chat_id, message_id=message_id, kind=kind, entity_id=entity_id))
            chat = (await session.execute(
                select(PromoChat).where(PromoChat.chat_id == chat_id)
            )).scalar_one_or_none()
            if chat:
                chat.posts_count = (chat.posts_count or 0) + 1
            await session.commit()
    except Exception as e:
        logger.exception("[CROSSPOST] Не удалось запомнить пост: %s", e)


async def _announce(
    session: AsyncSession, kind: str, entity_id: int,
    from_city: str, to_city: str, text: str, markup: dict | None,
) -> int:
    """Разослать объявление по подходящим чатам. Возвращает число чатов."""
    chats = await get_target_chats(session, from_city, to_city, kind)
    for chat in chats:
        # Каждое объявление уходит в фоне: рассылка не должна задерживать ответ API
        fire_and_forget(_post_and_remember(chat.chat_id, kind, entity_id, text, markup))

    if chats:
        logger.info("[CROSSPOST] %s %s разослан в чаты: %s", kind, entity_id, len(chats))
    return len(chats)


async def announce_flight(session: AsyncSession, flight: Flight) -> int:
    """Разослать объявление о рейсе по подключённым чатам."""
    traveler = await session.get(User, flight.traveler_id)
    if not traveler:
        return 0
    return await _announce(
        session, KIND_FLIGHT, flight.id, flight.from_city, flight.to_city,
        flight_text(flight, traveler),
        _markup(nt("ru", "btn_send_with_him"), deeplinks.flight_param(flight.id)),
    )


async def announce_parcel(session: AsyncSession, parcel: Parcel) -> int:
    """Разослать объявление о посылке по подключённым чатам."""
    # Посылка, адресованная конкретному перевозчику, в общий эфир не идёт
    if parcel.traveler_id:
        return 0
    sender = await session.get(User, parcel.sender_id)
    if not sender:
        return 0
    return await _announce(
        session, KIND_PARCEL, parcel.id, parcel.from_city, parcel.to_city,
        parcel_text(parcel, sender),
        _markup(nt("ru", "btn_take_parcel"), deeplinks.parcel_param(parcel.id)),
    )


# === Закрытие постов ===

async def _close_post_message(chat_id: int, message_id: int, text: str) -> None:
    """Фон: пометить пост закрытым и снять кнопку."""
    await edit_message_text(chat_id, message_id, text + nt("ru", "crosspost_closed"))


async def close_posts(session: AsyncSession, kind: str, entity_id: int, text: str) -> int:
    """Пометить все посты сущности закрытыми. Возвращает число постов."""
    posts = list((await session.execute(
        select(GroupPost).where(
            GroupPost.kind == kind,
            GroupPost.entity_id == entity_id,
            GroupPost.is_closed == False,  # noqa: E712
        )
    )).scalars().all())

    for post in posts:
        post.is_closed = True
        fire_and_forget(_close_post_message(post.chat_id, post.message_id, text))

    if posts:
        await session.commit()
        logger.info("[CROSSPOST] Закрыто постов %s#%s: %s", kind, entity_id, len(posts))
    return len(posts)


async def close_parcel_posts(session: AsyncSession, parcel: Parcel) -> int:
    """Посылку забрали или отменили — закрыть её объявления."""
    sender = await session.get(User, parcel.sender_id)
    if not sender:
        return 0
    return await close_posts(session, KIND_PARCEL, parcel.id, parcel_text(parcel, sender))


async def close_flight_posts(session: AsyncSession, flight: Flight) -> int:
    """Рейс отменён или завершён — закрыть его объявления."""
    traveler = await session.get(User, flight.traveler_id)
    if not traveler:
        return 0
    return await close_posts(session, KIND_FLIGHT, flight.id, flight_text(flight, traveler))


# === Реестр групп ===

@dataclass
class ResolveResult:
    """Итог подключения группы по ссылке."""
    chat: PromoChat | None = None
    reason: str | None = None  # bad_link / invite_link / not_found / not_group / no_token


def parse_group_link(raw: str) -> tuple[int | str | None, str | None]:
    """Разобрать ввод администратора в цель для getChat.

    Понимает: @username, t.me/username, t.me/c/<id>/..., -100<id>, число.
    Инвайт-ссылки (t.me/+..., joinchat) разобрать нельзя — по ним getChat не работает.
    """
    value = (raw or "").strip()
    if not value:
        return None, "bad_link"

    # Инвайт-ссылки не содержат идентификатора чата
    if "joinchat" in value or "/+" in value or value.startswith("+"):
        return None, "invite_link"

    # Голый числовой chat_id (у групп отрицательный)
    if value.lstrip("-").isdigit():
        return int(value), None

    # Убираем протокол и домен
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    for domain in ("t.me/", "telegram.me/", "telegram.dog/"):
        if value.startswith(domain):
            value = value[len(domain):]

    # Ссылка на приватный чат: t.me/c/<internal_id>/<msg>
    if value.startswith("c/"):
        internal = value[2:].split("/")[0]
        if internal.isdigit():
            return int(f"-100{internal}"), None
        return None, "bad_link"

    # @username или username
    username = value.lstrip("@").split("/")[0].split("?")[0]
    if username and username.replace("_", "").isalnum():
        return f"@{username}", None

    return None, "bad_link"


async def upsert_chat(
    session: AsyncSession,
    chat_id: int,
    title: str | None,
    username: str | None = None,
    chat_type: str | None = None,
    added_by: int | None = None,
    is_member: bool = True,
) -> PromoChat:
    """Создать или обновить запись группы в реестре."""
    chat = (await session.execute(
        select(PromoChat).where(PromoChat.chat_id == chat_id)
    )).scalar_one_or_none()

    if chat:
        # Повторное подключение обновляет карточку и членство
        chat.title = title or chat.title
        chat.username = username or chat.username
        chat.chat_type = chat_type or chat.chat_type
        chat.is_member = is_member
    else:
        chat = PromoChat(
            chat_id=chat_id, title=title, username=username, chat_type=chat_type,
            added_by=added_by, is_member=is_member, is_active=True,
        )
        session.add(chat)

    await session.commit()
    await session.refresh(chat)
    logger.info("[CROSSPOST] Чат в реестре: %s (%s), member=%s", chat_id, title, is_member)
    return chat


async def on_my_chat_member(
    session: AsyncSession, chat: dict, new_status: str, added_by: int | None = None,
) -> PromoChat | None:
    """Бота добавили в группу или выгнали — обновить реестр.

    `chat` — словарь chat из апдейта Telegram (id, type, title, username).
    """
    # Личные чаты реестру не нужны
    if chat.get("type") not in GROUP_CHAT_TYPES:
        return None

    is_member = new_status in MEMBER_STATUSES
    return await upsert_chat(
        session, chat_id=chat["id"], title=chat.get("title"), username=chat.get("username"),
        chat_type=chat.get("type"), added_by=added_by, is_member=is_member,
    )


async def resolve_link(session: AsyncSession, raw: str, added_by: int | None = None) -> ResolveResult:
    """Подключить группу по ссылке/@username/ID. Бот уже должен состоять в ней."""
    target, reason = parse_group_link(raw)
    if reason:
        return ResolveResult(reason=reason)

    if not settings.bot_token:
        return ResolveResult(reason="no_token")

    info = await call_api("getChat", {"chat_id": target})
    if not info:
        return ResolveResult(reason="not_found")
    if info.get("type") not in GROUP_CHAT_TYPES:
        return ResolveResult(reason="not_group")

    chat = await upsert_chat(
        session, chat_id=info["id"], title=info.get("title"), username=info.get("username"),
        chat_type=info.get("type"), added_by=added_by, is_member=True,
    )
    return ResolveResult(chat=chat)


async def list_chats(session: AsyncSession) -> list[PromoChat]:
    """Все группы реестра, активные первыми."""
    return list((await session.execute(
        select(PromoChat).order_by(PromoChat.is_active.desc(), PromoChat.id.desc())
    )).scalars().all())


async def get_chat(session: AsyncSession, chat_pk: int) -> PromoChat | None:
    """Группа по внутреннему id."""
    return await session.get(PromoChat, chat_pk)


async def update_chat(session: AsyncSession, chat: PromoChat, **fields) -> PromoChat:
    """Изменить настройки группы: включена, что постить, фильтр городов."""
    allowed = {"is_active", "post_parcels", "post_flights", "cities", "title"}
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(chat, key, value)
    await session.commit()
    await session.refresh(chat)
    return chat


async def delete_chat(session: AsyncSession, chat: PromoChat) -> None:
    """Убрать группу из реестра совсем."""
    await session.delete(chat)
    await session.commit()
    logger.info("[CROSSPOST] Чат удалён из реестра: %s", chat.chat_id)


# === Совместимость с командами бота в группе ===

async def add_chat(
    session: AsyncSession, chat_id: int, title: str | None, added_by: int | None,
) -> PromoChat:
    """Подключить чат к рассылке (команда /promo_add в группе)."""
    chat = await upsert_chat(session, chat_id=chat_id, title=title, added_by=added_by)
    if not chat.is_active:
        chat.is_active = True
        await session.commit()
    return chat


async def remove_chat(session: AsyncSession, chat_id: int) -> bool:
    """Отключить чат от рассылки (команда /promo_off). Запись остаётся ради истории."""
    chat = (await session.execute(
        select(PromoChat).where(PromoChat.chat_id == chat_id)
    )).scalar_one_or_none()
    if not chat:
        return False

    chat.is_active = False
    await session.commit()
    logger.info("[CROSSPOST] Чат отключён: %s", chat_id)
    return True
