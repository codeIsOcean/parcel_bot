"""Админ-панель: доступ, статистика, управление людьми, посылками, рейсами.

Администратор — это владелец из ADMIN_IDS (.env) или пользователь с флагом
is_admin, назначенный из панели. Владельцев из .env снять нельзя.

Все функции тонкие: считают, ищут, меняют флаги и зовут существующие
сервисы (баланс, кросс-постинг, уведомления), чтобы админские действия
проходили через ту же логику, что и обычные.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services import balance_service, crosspost_service, flight_service, notification_service
from shared.models.flight import Flight, FlightStatus
from shared.models.match import Match
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.payment import Payment, PaymentStatus
from shared.models.promo_chat import GroupPost, PromoChat
from shared.models.report import Report, ReportStatus
from shared.models.review import Review
from shared.models.user import User, UserRole

logger = logging.getLogger(__name__)


# === Доступ ===

def is_env_admin(user_id: int) -> bool:
    """Владелец из .env — админ всегда."""
    return user_id in settings.admin_id_list


def is_admin(user: User) -> bool:
    """Есть ли у пользователя доступ к админ-панели."""
    return is_env_admin(user.id) or bool(user.is_admin)


class AdminActionError(Exception):
    """Действие невозможно: причина в reason (для кода ответа API)."""

    def __init__(self, reason: str, status: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.status = status


# === Статистика ===

def _today_start() -> datetime:
    """Начало сегодняшнего дня в UTC."""
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def _count(session: AsyncSession, stmt) -> int:
    """Число строк для select-запроса."""
    return (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0


async def get_stats(session: AsyncSession) -> dict:
    """Сводка по сервису для главного экрана панели."""
    today = _today_start()
    week_ago = today - timedelta(days=7)

    users_total = await _count(session, select(User.id))
    users_today = await _count(session, select(User.id).where(User.created_at >= today))
    users_week = await _count(session, select(User.id).where(User.created_at >= week_ago))
    users_with_phone = await _count(session, select(User.id).where(User.phone.isnot(None)))
    users_blocked = await _count(session, select(User.id).where(User.is_blocked == True))  # noqa: E712
    travelers = await _count(session, select(User.id).where(User.role.in_((UserRole.TRAVELER, UserRole.BOTH))))

    parcels_total = await _count(session, select(Parcel.id))
    parcels_open = await _count(session, select(Parcel.id).where(Parcel.status == ParcelStatus.PENDING))
    parcels_active = await _count(session, select(Parcel.id).where(
        Parcel.status.in_((ParcelStatus.ACCEPTED, ParcelStatus.HANDED, ParcelStatus.IN_TRANSIT))
    ))
    parcels_delivered = await _count(session, select(Parcel.id).where(Parcel.status == ParcelStatus.DELIVERED))
    parcels_today = await _count(session, select(Parcel.id).where(Parcel.created_at >= today))

    flights_total = await _count(session, select(Flight.id))
    flights_active = await _count(session, select(Flight.id).where(Flight.status == FlightStatus.ACTIVE))
    flights_today = await _count(session, select(Flight.id).where(Flight.created_at >= today))

    matches_total = await _count(session, select(Match.id))
    reports_open = await _count(session, select(Report.id).where(Report.status == ReportStatus.OPEN))

    groups_active = await _count(session, select(PromoChat.id).where(
        PromoChat.is_active == True, PromoChat.is_member == True  # noqa: E712
    ))
    posts_total = await _count(session, select(GroupPost.id))

    # Выручка: завершённые платежи в звёздах
    stars_row = (await session.execute(
        select(func.coalesce(func.sum(Payment.amount_stars), 0), func.count(Payment.id))
        .where(Payment.status == PaymentStatus.COMPLETED)
    )).one()
    stars_today = (await session.execute(
        select(func.coalesce(func.sum(Payment.amount_stars), 0))
        .where(Payment.status == PaymentStatus.COMPLETED, Payment.completed_at >= today)
    )).scalar() or 0

    rating_row = (await session.execute(
        select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id))
    )).one()

    return {
        "users": {
            "total": users_total, "today": users_today, "week": users_week,
            "with_phone": users_with_phone, "blocked": users_blocked, "travelers": travelers,
        },
        "parcels": {
            "total": parcels_total, "open": parcels_open, "active": parcels_active,
            "delivered": parcels_delivered, "today": parcels_today,
        },
        "flights": {"total": flights_total, "active": flights_active, "today": flights_today},
        "matches": {"total": matches_total},
        "reports": {"open": reports_open},
        "groups": {"active": groups_active, "posts": posts_total},
        "revenue": {
            "stars_total": int(stars_row[0] or 0), "payments": int(stars_row[1] or 0),
            "stars_today": int(stars_today),
        },
        "reviews": {"total": int(rating_row[1] or 0), "avg": round(float(rating_row[0] or 0), 2)},
    }


# === Пользователи ===

def user_row(user: User) -> dict:
    """Карточка пользователя для панели — с приватными полями."""
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "phone": user.phone,
        "city": user.city,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "lang": user.lang,
        "rating": user.rating,
        "reviews_count": user.reviews_count,
        "deliveries_count": user.deliveries_count,
        "reports_count": user.reports_count,
        "balance_stars": user.balance_stars,
        "trial_days_left": user.trial_days_left,
        "last_fee_date": user.last_fee_date,
        "is_verified": user.is_verified,
        "is_premium": user.is_premium,
        "is_blocked": user.is_blocked,
        "is_admin": is_admin(user),
        "is_env_admin": is_env_admin(user.id),
        "bot_blocked": user.bot_blocked,
        "created_at": user.created_at,
    }


async def search_users(
    session: AsyncSession, q: str | None = None, only: str | None = None,
    page: int = 1, limit: int = 20,
) -> tuple[list[User], int]:
    """Поиск по id, username, имени или телефону. Фильтр only: blocked / admins / travelers."""
    stmt = select(User)
    if q:
        needle = q.strip().lstrip("@")
        conditions = [
            User.username.ilike(f"%{needle}%"),
            User.first_name.ilike(f"%{needle}%"),
            User.last_name.ilike(f"%{needle}%"),
            User.phone.ilike(f"%{needle}%"),
        ]
        # Число — это ещё и telegram id
        if needle.isdigit():
            conditions.append(User.id == int(needle))
        stmt = stmt.where(or_(*conditions))

    if only == "blocked":
        stmt = stmt.where(User.is_blocked == True)  # noqa: E712
    elif only == "admins":
        stmt = stmt.where(User.is_admin == True)  # noqa: E712
    elif only == "travelers":
        stmt = stmt.where(User.role.in_((UserRole.TRAVELER, UserRole.BOTH)))
    elif only == "reported":
        stmt = stmt.where(User.reports_count > 0)

    total = await _count(session, stmt)
    rows = (await session.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()
    return list(rows), total


async def get_user(session: AsyncSession, user_id: int) -> User:
    """Пользователь или ошибка 404."""
    user = await session.get(User, user_id)
    if not user:
        raise AdminActionError("user_not_found", 404)
    return user


async def set_blocked(session: AsyncSession, actor: User, user_id: int, blocked: bool) -> User:
    """Заблокировать или разблокировать. Себя и владельцев из .env — нельзя."""
    user = await get_user(session, user_id)
    if blocked and (user.id == actor.id or is_env_admin(user.id)):
        raise AdminActionError("cannot_block_admin", 400)

    user.is_blocked = blocked
    await session.commit()
    await session.refresh(user)

    # Человек узнаёт о решении в боте
    notification_service.notify_admin_block(user, blocked)
    logger.info("[ADMIN] %s: user=%s by=%s", "block" if blocked else "unblock", user_id, actor.id)
    return user


async def set_verified(session: AsyncSession, actor: User, user_id: int, verified: bool) -> User:
    """Поставить или снять галочку проверенного."""
    user = await get_user(session, user_id)
    user.is_verified = verified
    await session.commit()
    await session.refresh(user)
    logger.info("[ADMIN] verified=%s: user=%s by=%s", verified, user_id, actor.id)
    return user


async def set_admin(session: AsyncSession, actor: User, user_id: int, admin: bool) -> User:
    """Назначить или снять администратора. Владельца из .env снять нельзя."""
    user = await get_user(session, user_id)
    if not admin and is_env_admin(user.id):
        raise AdminActionError("cannot_revoke_env_admin", 400)
    if not admin and user.id == actor.id:
        raise AdminActionError("cannot_revoke_self", 400)

    user.is_admin = admin
    await session.commit()
    await session.refresh(user)
    logger.info("[ADMIN] admin=%s: user=%s by=%s", admin, user_id, actor.id)
    return user


async def adjust_balance(
    session: AsyncSession, actor: User, user_id: int, delta: int, note: str | None = None,
) -> int:
    """Начислить (delta > 0) или списать (delta < 0) звёзды вручную."""
    user = await get_user(session, user_id)
    if delta == 0:
        raise AdminActionError("bad_amount", 400)

    reason = f"admin:{actor.id}:{note or ''}".strip(":")
    if delta > 0:
        result = await balance_service.top_up(session, user_id, delta, note=reason)
    else:
        result = await balance_service.charge(session, user_id, -delta, note=reason)
    if not result.ok:
        raise AdminActionError(result.reason or "balance_error", 400)

    await session.refresh(user)
    notification_service.notify_admin_balance(user, delta, result.balance)
    logger.info("[ADMIN] balance %+d: user=%s by=%s", delta, user_id, actor.id)
    return result.balance


# === Посылки и рейсы ===

async def list_parcels(
    session: AsyncSession, status: str | None = None, q: str | None = None,
    page: int = 1, limit: int = 20,
) -> tuple[list[dict], int]:
    """Посылки с именами сторон."""
    stmt = select(Parcel)
    if status and status in [s.value for s in ParcelStatus]:
        stmt = stmt.where(Parcel.status == ParcelStatus(status))
    if q:
        needle = q.strip()
        conditions = [Parcel.from_city.ilike(f"%{needle}%"), Parcel.to_city.ilike(f"%{needle}%"),
                      Parcel.description.ilike(f"%{needle}%")]
        if needle.isdigit():
            conditions += [Parcel.id == int(needle), Parcel.sender_id == int(needle)]
        stmt = stmt.where(or_(*conditions))

    total = await _count(session, stmt)
    parcels = (await session.execute(
        stmt.order_by(Parcel.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()

    items = []
    for parcel in parcels:
        sender = await session.get(User, parcel.sender_id)
        traveler = await session.get(User, parcel.traveler_id) if parcel.traveler_id else None
        items.append({
            "id": parcel.id,
            "from_city": parcel.from_city, "to_city": parcel.to_city,
            "description": parcel.description, "weight": parcel.weight, "price": parcel.price,
            "status": parcel.status.value,
            "sender_id": parcel.sender_id, "sender_name": sender.full_name if sender else None,
            "traveler_id": parcel.traveler_id, "traveler_name": traveler.full_name if traveler else None,
            "created_at": parcel.created_at,
        })
    return items, total


async def cancel_parcel(session: AsyncSession, actor: User, parcel_id: int) -> Parcel:
    """Принудительно отменить посылку."""
    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        raise AdminActionError("parcel_not_found", 404)
    if parcel.status in (ParcelStatus.DELIVERED, ParcelStatus.CANCELLED):
        raise AdminActionError("parcel_closed", 400)

    parcel.status = ParcelStatus.CANCELLED
    await session.commit()
    await session.refresh(parcel)

    # Объявления в группах закрываем
    await crosspost_service.close_parcel_posts(session, parcel)
    logger.info("[ADMIN] parcel cancelled: %s by=%s", parcel_id, actor.id)
    return parcel


async def list_flights(
    session: AsyncSession, status: str | None = None, q: str | None = None,
    page: int = 1, limit: int = 20,
) -> tuple[list[dict], int]:
    """Рейсы с именем перевозчика."""
    stmt = select(Flight)
    if status and status in [s.value for s in FlightStatus]:
        stmt = stmt.where(Flight.status == FlightStatus(status))
    if q:
        needle = q.strip()
        conditions = [Flight.from_city.ilike(f"%{needle}%"), Flight.to_city.ilike(f"%{needle}%")]
        if needle.isdigit():
            conditions += [Flight.id == int(needle), Flight.traveler_id == int(needle)]
        stmt = stmt.where(or_(*conditions))

    total = await _count(session, stmt)
    flights = (await session.execute(
        stmt.order_by(Flight.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()

    items = []
    for flight in flights:
        traveler = await session.get(User, flight.traveler_id)
        items.append({
            "id": flight.id,
            "from_city": flight.from_city, "to_city": flight.to_city,
            "flight_date": flight.flight_date, "available_kg": flight.available_kg,
            "price_per_kg": flight.price_per_kg, "status": flight.status.value,
            "requests_count": flight.requests_count,
            "traveler_id": flight.traveler_id, "traveler_name": traveler.full_name if traveler else None,
            "created_at": flight.created_at,
        })
    return items, total


async def cancel_flight(session: AsyncSession, actor: User, flight_id: int) -> Flight:
    """Принудительно отменить рейс."""
    flight = await flight_service.cancel_flight(session, flight_id)
    if not flight:
        raise AdminActionError("flight_not_found_or_closed", 400)
    logger.info("[ADMIN] flight cancelled: %s by=%s", flight_id, actor.id)
    return flight


# === Жалобы ===

async def list_reports(session: AsyncSession, status: str | None = "open", limit: int = 50) -> list[dict]:
    """Жалобы с именами сторон."""
    stmt = select(Report)
    if status and status in [s.value for s in ReportStatus]:
        stmt = stmt.where(Report.status == ReportStatus(status))
    reports = (await session.execute(stmt.order_by(Report.created_at.desc()).limit(limit))).scalars().all()

    items = []
    for report in reports:
        author = await session.get(User, report.author_id)
        target = await session.get(User, report.target_id)
        items.append({
            "id": report.id,
            "reason": report.reason.value, "comment": report.comment, "status": report.status.value,
            "parcel_id": report.parcel_id,
            "author_id": report.author_id, "author_name": author.full_name if author else None,
            "target_id": report.target_id, "target_name": target.full_name if target else None,
            "target_blocked": bool(target and target.is_blocked),
            "created_at": report.created_at,
        })
    return items


async def resolve_report(session: AsyncSession, actor: User, report_id: int, status: str) -> Report:
    """Закрыть жалобу: reviewed (мер нет) или confirmed (меры приняты)."""
    report = await session.get(Report, report_id)
    if not report:
        raise AdminActionError("report_not_found", 404)
    if status not in (ReportStatus.REVIEWED.value, ReportStatus.CONFIRMED.value):
        raise AdminActionError("bad_status", 400)

    report.status = ReportStatus(status)
    await session.commit()
    await session.refresh(report)
    logger.info("[ADMIN] report %s -> %s by=%s", report_id, status, actor.id)
    return report


# === Платежи ===

async def list_payments(session: AsyncSession, page: int = 1, limit: int = 30) -> tuple[list[dict], int]:
    """Платежи, новые первыми."""
    stmt = select(Payment)
    total = await _count(session, stmt)
    payments = (await session.execute(
        stmt.order_by(Payment.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()

    items = []
    for payment in payments:
        user = await session.get(User, payment.user_id)
        items.append({
            "id": payment.id,
            "user_id": payment.user_id, "user_name": user.full_name if user else None,
            "amount": payment.amount, "amount_stars": payment.amount_stars, "amount_ton": payment.amount_ton,
            "method": payment.method.value, "status": payment.status.value, "kind": payment.kind.value,
            "created_at": payment.created_at, "completed_at": payment.completed_at,
        })
    return items, total


# === Рассылка ===

async def broadcast_targets(session: AsyncSession, audience: str) -> list[User]:
    """Кому слать: all / senders / travelers / with_phone."""
    stmt = select(User).where(User.is_blocked == False, User.bot_blocked == False)  # noqa: E712
    if audience == "travelers":
        stmt = stmt.where(User.role.in_((UserRole.TRAVELER, UserRole.BOTH)))
    elif audience == "senders":
        stmt = stmt.where(User.role.in_((UserRole.SENDER, UserRole.BOTH)))
    elif audience == "with_phone":
        stmt = stmt.where(User.phone.isnot(None))
    elif audience != "all":
        raise AdminActionError("bad_audience", 400)
    return list((await session.execute(stmt)).scalars().all())


async def broadcast(session: AsyncSession, actor: User, audience: str, text: str) -> int:
    """Разослать сообщение аудитории. Возвращает число адресатов."""
    users = await broadcast_targets(session, audience)
    from shared.notify import webapp_button
    from shared.locale.notify_texts import nt

    for user in users:
        notification_service.notify(user, text, webapp_button(nt(user.lang, "btn_open_app"), "/"))

    logger.info("[ADMIN] broadcast to %s (%s) by=%s", len(users), audience, actor.id)
    return len(users)
