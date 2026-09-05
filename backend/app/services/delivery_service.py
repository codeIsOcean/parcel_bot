"""Жизненный цикл доставки: передача, вылет, прилёт, выдача.

Раньше статус посылки застревал на «принято» — дальше его никто не двигал.
Здесь каждый переход подтверждается действием перевозчика, а отправитель
получает уведомление, чтобы не спрашивать «ну как там».

Выдача закрывается кодом: отправитель получает его при передаче посылки
и называет получателю, перевозчик вводит код при выдаче.
"""

import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services import notification_service
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.user import User

logger = logging.getLogger(__name__)

# Длина кода выдачи
HANDOVER_CODE_LENGTH = 4


class DeliveryError(Exception):
    """Недопустимый переход или неверный код."""


def generate_handover_code() -> str:
    """Сгенерировать код выдачи. Короткий, чтобы его можно было продиктовать."""
    # secrets, а не random: код подтверждает факт выдачи
    return "".join(secrets.choice("0123456789") for _ in range(HANDOVER_CODE_LENGTH))


def _now() -> datetime:
    """Текущее время в UTC."""
    return datetime.now(timezone.utc)


async def _load_for_traveler(session: AsyncSession, parcel_id: int, actor_id: int) -> Parcel:
    """Загрузить посылку и убедиться, что действие совершает её перевозчик."""
    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        raise DeliveryError("Parcel not found")

    # Двигать статус может только тот, кто везёт посылку
    if parcel.traveler_id != actor_id:
        raise DeliveryError("Not authorized: you are not the traveler of this parcel")

    return parcel


async def mark_handed(
    session: AsyncSession,
    parcel_id: int,
    actor_id: int,
    photo_file_ids: str | None = None,
) -> Parcel:
    """Перевозчик подтверждает, что забрал посылку у отправителя."""
    parcel = await _load_for_traveler(session, parcel_id, actor_id)

    if parcel.status != ParcelStatus.ACCEPTED:
        raise DeliveryError(f"Cannot hand over parcel in status {parcel.status.value}")

    parcel.status = ParcelStatus.HANDED
    parcel.handed_at = _now()
    parcel.handover_photo_file_ids = photo_file_ids

    # Код выдачи создаём один раз и отдаём отправителю
    if not parcel.handover_code:
        parcel.handover_code = generate_handover_code()

    await session.commit()
    await session.refresh(parcel)

    await notification_service.notify_parcel_handed(session, parcel)
    logger.info("[DELIVERY] Передана перевозчику: parcel=%s", parcel_id)
    return parcel


async def mark_in_transit(session: AsyncSession, parcel_id: int, actor_id: int) -> Parcel:
    """Перевозчик отмечает вылет."""
    parcel = await _load_for_traveler(session, parcel_id, actor_id)

    if parcel.status != ParcelStatus.HANDED:
        raise DeliveryError(f"Cannot start transit from status {parcel.status.value}")

    parcel.status = ParcelStatus.IN_TRANSIT
    parcel.in_transit_at = _now()
    await session.commit()
    await session.refresh(parcel)

    await notification_service.notify_parcel_in_transit(session, parcel)
    logger.info("[DELIVERY] В пути: parcel=%s", parcel_id)
    return parcel


async def mark_arrived(session: AsyncSession, parcel_id: int, actor_id: int) -> Parcel:
    """Перевозчик отмечает прилёт. Статус не меняется, меняется отметка времени."""
    parcel = await _load_for_traveler(session, parcel_id, actor_id)

    if parcel.status != ParcelStatus.IN_TRANSIT:
        raise DeliveryError(f"Cannot mark arrival from status {parcel.status.value}")

    # Повторный вызов не должен слать отправителю второе уведомление
    if parcel.arrived_at:
        return parcel

    parcel.arrived_at = _now()
    await session.commit()
    await session.refresh(parcel)

    await notification_service.notify_parcel_arrived(session, parcel)
    logger.info("[DELIVERY] Прилетела: parcel=%s", parcel_id)
    return parcel


async def mark_delivered(
    session: AsyncSession,
    parcel_id: int,
    actor_id: int,
    code: str,
    photo_file_ids: str | None = None,
) -> Parcel:
    """Перевозчик закрывает доставку кодом, который назвал получатель."""
    parcel = await _load_for_traveler(session, parcel_id, actor_id)

    if parcel.status != ParcelStatus.IN_TRANSIT:
        raise DeliveryError(f"Cannot deliver parcel in status {parcel.status.value}")

    # Код обязателен: без него нельзя доказать, что посылка дошла
    if not parcel.handover_code:
        raise DeliveryError("Handover code is missing, contact support")

    # Сравнение без учёта пробелов, которые пользователь может ввести случайно
    if (code or "").strip() != parcel.handover_code:
        logger.info("[DELIVERY] Неверный код выдачи: parcel=%s", parcel_id)
        raise DeliveryError("Invalid handover code")

    parcel.status = ParcelStatus.DELIVERED
    parcel.delivered_at = _now()
    parcel.delivery_photo_file_ids = photo_file_ids

    # Счётчик доставок — основа репутации перевозчика
    traveler = await session.get(User, actor_id)
    if traveler:
        traveler.deliveries_count = (traveler.deliveries_count or 0) + 1
        # Галочка выдаётся автоматически после нескольких закрытых доставок
        if (
            not traveler.is_verified
            and traveler.deliveries_count >= settings.verified_deliveries_threshold
        ):
            traveler.is_verified = True
            logger.info("[DELIVERY] Перевозчик верифицирован: user=%s", actor_id)

    await session.commit()
    await session.refresh(parcel)

    await notification_service.notify_parcel_delivered(session, parcel)
    logger.info("[DELIVERY] Доставлена: parcel=%s, traveler=%s", parcel_id, actor_id)
    return parcel


def timeline(parcel: Parcel) -> list[dict]:
    """Этапы доставки для экрана отслеживания."""
    # Порядок фиксированный: фронт рисует его как вертикальный таймлайн
    steps = [
        ("created", parcel.created_at),
        ("accepted", parcel.handed_at and parcel.created_at or None),
        ("handed", parcel.handed_at),
        ("in_transit", parcel.in_transit_at),
        ("arrived", parcel.arrived_at),
        ("delivered", parcel.delivered_at),
    ]

    # Шаг «принято» отмечаем по факту наличия перевозчика, а не по времени
    result = []
    for key, at in steps:
        if key == "accepted":
            done = parcel.traveler_id is not None
            at = None
        else:
            done = at is not None
        result.append({
            "key": key,
            "done": done,
            "at": at.isoformat() if at else None,
        })
    return result
