import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services import moderation_service, notification_service
from shared.models.parcel import Parcel, ParcelStatus, ParcelSize

logger = logging.getLogger(__name__)


async def create_parcel(
    session: AsyncSession,
    sender_id: int,
    from_city: str,
    to_city: str,
    description: str,
    weight: float,
    size: str,
    price: float,
    traveler_id: int | None = None,
) -> Parcel:
    """Создать новую посылку."""
    logger.info(
        "[PARCEL] Создание: sender=%s, route=%s→%s, weight=%s, price=%s",
        sender_id, from_city, to_city, weight, price,
    )

    # Запрещённое вложение отсекаем до записи в базу — перевозчик рискует на границе
    moderation_service.ensure_allowed(description)

    # Создаём запись в БД
    parcel = Parcel(
        sender_id=sender_id,
        from_city=from_city,
        to_city=to_city,
        description=description,
        weight=weight,
        size=ParcelSize(size) if size in [e.value for e in ParcelSize] else ParcelSize.MEDIUM,
        price=price,
        traveler_id=traveler_id,
        status=ParcelStatus.PENDING,
    )
    session.add(parcel)
    await session.commit()
    await session.refresh(parcel)

    # Если подходящие рейсы уже опубликованы — отправитель узнаёт об этом сразу
    await notification_service.notify_matches_for_new_parcel(session, parcel)

    logger.info("[PARCEL] Создана: parcel_id=%s", parcel.id)
    return parcel


async def get_user_parcels(
    session: AsyncSession,
    user_id: int,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Parcel], int]:
    """Получить посылки пользователя с пагинацией."""
    # Базовый запрос — посылки отправителя
    query = select(Parcel).where(Parcel.sender_id == user_id)

    # Фильтр по статусу
    if status:
        if status == "active":
            query = query.where(Parcel.status.in_([
                ParcelStatus.PENDING, ParcelStatus.ACCEPTED,
                ParcelStatus.HANDED, ParcelStatus.IN_TRANSIT,
            ]))
        elif status == "completed":
            query = query.where(Parcel.status.in_([
                ParcelStatus.DELIVERED, ParcelStatus.CANCELLED,
            ]))
        else:
            try:
                query = query.where(Parcel.status == ParcelStatus(status))
            except ValueError:
                pass  # Неизвестный статус — не фильтруем

    # Считаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Пагинация и сортировка
    query = query.order_by(Parcel.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await session.execute(query)
    parcels = list(result.scalars().all())

    return parcels, total


async def get_parcel_by_id(session: AsyncSession, parcel_id: int) -> Parcel | None:
    """Получить посылку по ID."""
    result = await session.execute(select(Parcel).where(Parcel.id == parcel_id))
    return result.scalar_one_or_none()


async def cancel_parcel(session: AsyncSession, parcel_id: int, user_id: int) -> Parcel | None:
    """Отменить посылку (только отправитель, только если pending/accepted)."""
    parcel = await get_parcel_by_id(session, parcel_id)

    # Проверяем владельца и статус
    if not parcel or parcel.sender_id != user_id:
        return None
    if parcel.status not in (ParcelStatus.PENDING, ParcelStatus.ACCEPTED):
        return None

    # Меняем статус
    parcel.status = ParcelStatus.CANCELLED
    await session.commit()
    await session.refresh(parcel)

    logger.info("[PARCEL] Отменена: parcel_id=%s, user=%s", parcel_id, user_id)
    return parcel


async def accept_parcel(
    session: AsyncSession,
    parcel_id: int,
    traveler_id: int,
) -> Parcel:
    """Перевозчик принимает посылку."""
    parcel = await get_parcel_by_id(session, parcel_id)
    if not parcel:
        raise ValueError("Parcel not found")
    if parcel.status != ParcelStatus.PENDING:
        raise ValueError("Parcel is not pending")

    parcel.traveler_id = traveler_id
    parcel.status = ParcelStatus.ACCEPTED
    await session.commit()
    await session.refresh(parcel)

    logger.info("[PARCEL] Принята: parcel=%s, traveler=%s", parcel_id, traveler_id)
    return parcel


async def get_traveler_parcels(
    session: AsyncSession,
    traveler_id: int,
    page: int = 1,
    limit: int = 20,
) -> tuple[list["Parcel"], int]:
    """Получить посылки, назначенные перевозчику."""
    query = select(Parcel).where(Parcel.traveler_id == traveler_id)
    query = query.order_by(Parcel.created_at.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * limit).limit(limit)
    result = await session.execute(query)
    parcels = list(result.scalars().all())

    return parcels, total
