"""Бизнес-уведомления в Telegram.

Правило: текст уведомления собирается синхронно, пока жива сессия запроса,
а сама отправка уходит в фон. Так ответ API не ждёт Telegram, а фоновая
задача не трогает уже закрытую сессию.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import deeplinks
from shared.locale.notify_texts import nt
from shared.models.flight import Flight, FlightStatus
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.user import User
from shared.notify import fire_and_forget, send_message, webapp_button

logger = logging.getLogger(__name__)

# Сколько подходящих рейсов показываем отправителю за раз
MATCH_NOTIFY_LIMIT = 3


def format_rating(user: User) -> str:
    """Рейтинг в виде компактной подписи. У новичка подписи нет."""
    if not user.reviews_count:
        return ""
    return f"⭐ {user.rating:.1f} ({user.reviews_count})"


async def _deliver(user_id: int, text: str, markup: dict | None) -> None:
    """Фоновая доставка: отправить и, если бот заблокирован, отметить это в БД."""
    result = await send_message(user_id, text, reply_markup=markup)

    # Пользователь заблокировал бота — больше ему не пишем
    if result.blocked:
        # Своя сессия: сессия запроса к этому моменту уже закрыта
        from backend.app.database import async_session

        try:
            async with async_session() as session:
                user = await session.get(User, user_id)
                if user and not user.bot_blocked:
                    user.bot_blocked = True
                    await session.commit()
                    logger.info("[NOTIFY] Отмечен bot_blocked: user=%s", user_id)
        except Exception as e:
            logger.exception("[NOTIFY] Не удалось отметить bot_blocked: %s", e)


def notify(user: User, text: str, markup: dict | None = None) -> None:
    """Поставить уведомление в очередь на отправку."""
    # Не тратим запросы на тех, кто заблокировал бота
    if user.bot_blocked:
        return
    fire_and_forget(_deliver(user.id, text, markup))


# === Заявки на перевозку ===

async def notify_new_request(session: AsyncSession, parcel: Parcel, flight: Flight) -> None:
    """Перевозчику: на его рейс поступила новая заявка."""
    traveler = await session.get(User, flight.traveler_id)
    sender = await session.get(User, parcel.sender_id)
    if not traveler or not sender:
        return

    text = nt(
        traveler.lang, "new_request",
        from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
        description=parcel.description, weight=parcel.weight, price=parcel.price,
        sender_name=sender.full_name, sender_rating=format_rating(sender),
    )
    notify(traveler, text, webapp_button(nt(traveler.lang, "btn_open_requests"), "/requests"))


async def notify_request_accepted(session: AsyncSession, parcel: Parcel, flight: Flight) -> None:
    """Отправителю: перевозчик принял его заявку."""
    sender = await session.get(User, parcel.sender_id)
    traveler = await session.get(User, flight.traveler_id)
    if not sender or not traveler:
        return

    text = nt(
        sender.lang, "request_accepted",
        traveler_name=traveler.full_name, traveler_rating=format_rating(traveler),
        from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
    )
    notify(sender, text, webapp_button(nt(sender.lang, "btn_open_tracking"), f"/tracking/{parcel.id}"))


async def notify_request_declined(session: AsyncSession, parcel: Parcel) -> None:
    """Отправителю: перевозчик отклонил заявку."""
    sender = await session.get(User, parcel.sender_id)
    if not sender:
        return

    text = nt(
        sender.lang, "request_declined",
        description=parcel.description,
        from_city=parcel.from_city, to_city=parcel.to_city,
    )
    notify(sender, text, webapp_button(nt(sender.lang, "btn_open_app"), "/travelers"))


# === Матчинг ===

async def find_flights_for_parcel(
    session: AsyncSession, parcel: Parcel, limit: int = MATCH_NOTIFY_LIMIT,
) -> list[Flight]:
    """Активные рейсы, которые подходят посылке по маршруту, дате и весу."""
    query = (
        select(Flight)
        .where(
            Flight.from_city == parcel.from_city,
            Flight.to_city == parcel.to_city,
            Flight.status == FlightStatus.ACTIVE,
            Flight.flight_date >= date.today(),
            Flight.available_kg >= parcel.weight,
            # Свой же рейс отправителю предлагать не надо
            Flight.traveler_id != parcel.sender_id,
        )
        .order_by(Flight.flight_date.asc())
        .limit(limit)
    )
    return list((await session.execute(query)).scalars().all())


async def find_parcels_for_flight(session: AsyncSession, flight: Flight) -> list[Parcel]:
    """Посылки, которые ждут отправки и влезают в этот рейс."""
    query = (
        select(Parcel)
        .where(
            Parcel.from_city == flight.from_city,
            Parcel.to_city == flight.to_city,
            Parcel.status == ParcelStatus.PENDING,
            Parcel.weight <= flight.available_kg,
            Parcel.sender_id != flight.traveler_id,
        )
        .order_by(Parcel.created_at.asc())
    )
    return list((await session.execute(query)).scalars().all())


async def notify_matches_for_new_parcel(session: AsyncSession, parcel: Parcel) -> None:
    """Отправителю: под его новую посылку уже есть подходящие рейсы."""
    flights = await find_flights_for_parcel(session, parcel)
    if not flights:
        return

    sender = await session.get(User, parcel.sender_id)
    if not sender:
        return

    for flight in flights:
        traveler = await session.get(User, flight.traveler_id)
        if not traveler:
            continue
        text = nt(
            sender.lang, "match_flight_for_parcel",
            from_city=flight.from_city, to_city=flight.to_city,
            flight_date=flight.flight_date.strftime("%d.%m.%Y"),
            traveler_name=traveler.full_name, traveler_rating=format_rating(traveler),
            available_kg=flight.available_kg, price_per_kg=flight.price_per_kg,
            description=parcel.description, weight=parcel.weight,
        )
        notify(sender, text, webapp_button(nt(sender.lang, "btn_open_app"), "/travelers"))

    logger.info("[MATCH] Отправителю %s предложено рейсов: %s", sender.id, len(flights))


async def notify_matches_for_new_flight(session: AsyncSession, flight: Flight) -> None:
    """Перевозчику — сводка по ждущим посылкам, отправителям — что нашёлся рейс."""
    parcels = await find_parcels_for_flight(session, flight)
    if not parcels:
        return

    traveler = await session.get(User, flight.traveler_id)
    if not traveler:
        return

    # 1. Перевозчику одно сводное сообщение, а не по письму на каждую посылку
    total_price = sum(p.price for p in parcels)
    text = nt(
        traveler.lang, "match_parcels_for_flight",
        from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
        count=len(parcels), total_price=round(total_price, 2),
    )
    notify(traveler, text, webapp_button(nt(traveler.lang, "btn_open_requests"), "/requests"))

    # 2. Каждому отправителю — что под его посылку появился рейс
    for parcel in parcels:
        sender = await session.get(User, parcel.sender_id)
        if not sender:
            continue
        sender_text = nt(
            sender.lang, "match_flight_for_parcel",
            from_city=flight.from_city, to_city=flight.to_city,
            flight_date=flight.flight_date.strftime("%d.%m.%Y"),
            traveler_name=traveler.full_name, traveler_rating=format_rating(traveler),
            available_kg=flight.available_kg, price_per_kg=flight.price_per_kg,
            description=parcel.description, weight=parcel.weight,
        )
        notify(sender, sender_text, webapp_button(nt(sender.lang, "btn_open_app"), "/travelers"))

    logger.info("[MATCH] Рейс %s: посылок найдено %s", flight.id, len(parcels))


# === Отклики перевозчиков ===

async def notify_offer_received(session: AsyncSession, parcel: Parcel, flight: Flight) -> None:
    """Отправителю: на его посылку откликнулся перевозчик."""
    sender = await session.get(User, parcel.sender_id)
    traveler = await session.get(User, flight.traveler_id)
    if not sender or not traveler:
        return

    text = nt(
        sender.lang, "offer_received",
        description=parcel.description, from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
        traveler_name=traveler.full_name, traveler_rating=format_rating(traveler),
        price_per_kg=flight.price_per_kg,
    )
    notify(sender, text, webapp_button(
        nt(sender.lang, "btn_open_parcel"), deeplinks.screen_path(deeplinks.parcel_param(parcel.id)),
    ))


async def notify_offer_accepted(session: AsyncSession, parcel: Parcel, flight: Flight) -> None:
    """Перевозчику: отправитель принял его отклик."""
    traveler = await session.get(User, flight.traveler_id)
    if not traveler:
        return

    text = nt(
        traveler.lang, "offer_accepted",
        description=parcel.description, from_city=flight.from_city, to_city=flight.to_city,
        flight_date=flight.flight_date.strftime("%d.%m.%Y"),
    )
    notify(traveler, text, webapp_button(nt(traveler.lang, "btn_open_chat"), "/chats"))


async def notify_offer_declined(session: AsyncSession, parcel: Parcel, flight: Flight) -> None:
    """Перевозчику: отправитель отклонил его отклик."""
    traveler = await session.get(User, flight.traveler_id)
    if not traveler:
        return

    text = nt(traveler.lang, "offer_declined", from_city=parcel.from_city, to_city=parcel.to_city)
    notify(traveler, text, webapp_button(nt(traveler.lang, "btn_open_app"), "/"))


# === Отзывы ===

def notify_review_replied(author: User, target: User, reply_text: str) -> None:
    """Автору отзыва: получатель ответил."""
    text = nt(author.lang, "review_replied", name=target.full_name, text=reply_text)
    notify(author, text, webapp_button(
        nt(author.lang, "btn_open_profile"), deeplinks.screen_path(f"profile_{target.id}"),
    ))


# === Действия администратора ===

def notify_admin_block(user: User, blocked: bool) -> None:
    """Пользователю: его заблокировали или разблокировали."""
    key = "admin_blocked" if blocked else "admin_unblocked"
    markup = None if blocked else webapp_button(nt(user.lang, "btn_open_app"), "/")
    # Заблокированному пишем даже если он раньше скрыл бота — это важное уведомление
    fire_and_forget(_deliver(user.id, nt(user.lang, key), markup))


def notify_admin_balance(user: User, delta: int, balance: int) -> None:
    """Пользователю: администратор изменил баланс."""
    sign = f"+{delta} ⭐" if delta > 0 else f"{delta} ⭐"
    notify(user, nt(user.lang, "admin_balance_changed", delta=sign, balance=balance),
           webapp_button(nt(user.lang, "btn_open_wallet"), "/wallet"))


# === Чат ===

async def notify_new_message(
    session: AsyncSession, recipient_id: int, sender_name: str, text: str, chat_id: int,
) -> None:
    """Собеседнику: пришло новое сообщение, пока Mini App был закрыт."""
    recipient = await session.get(User, recipient_id)
    if not recipient:
        return

    # Длинные сообщения обрезаем — это уведомление, а не доставка текста
    preview = text if len(text) <= 200 else text[:197] + "..."
    body = nt(recipient.lang, "new_message", sender_name=sender_name, text=preview)
    notify(recipient, body, webapp_button(nt(recipient.lang, "btn_open_chat"), f"/chats/{chat_id}"))


# === Этапы доставки ===

async def _notify_sender(session: AsyncSession, parcel: Parcel, key: str, path: str, btn: str) -> None:
    """Общая часть уведомлений отправителю о движении посылки."""
    sender = await session.get(User, parcel.sender_id)
    if not sender:
        return

    text = nt(
        sender.lang, key,
        description=parcel.description,
        from_city=parcel.from_city, to_city=parcel.to_city,
    )
    notify(sender, text, webapp_button(nt(sender.lang, btn), path))


async def notify_parcel_handed(session: AsyncSession, parcel: Parcel) -> None:
    """Отправителю: посылка у перевозчика, плюс код выдачи отдельным сообщением."""
    await _notify_sender(
        session, parcel, "parcel_handed", f"/tracking/{parcel.id}", "btn_open_tracking",
    )

    # Код уходит отдельно, чтобы его было легко найти в переписке
    sender = await session.get(User, parcel.sender_id)
    if sender and parcel.handover_code:
        notify(sender, nt(sender.lang, "handover_code", code=parcel.handover_code))


async def notify_parcel_in_transit(session: AsyncSession, parcel: Parcel) -> None:
    """Отправителю: перевозчик вылетел."""
    await _notify_sender(
        session, parcel, "parcel_in_transit", f"/tracking/{parcel.id}", "btn_open_tracking",
    )


async def notify_parcel_arrived(session: AsyncSession, parcel: Parcel) -> None:
    """Отправителю: перевозчик прилетел, пора забирать."""
    await _notify_sender(
        session, parcel, "parcel_arrived", f"/tracking/{parcel.id}", "btn_open_tracking",
    )


async def notify_parcel_delivered(session: AsyncSession, parcel: Parcel) -> None:
    """Отправителю: доставка закрыта, предлагаем оценить перевозчика."""
    await _notify_sender(
        session, parcel, "parcel_delivered", f"/rate/{parcel.id}", "btn_rate",
    )
