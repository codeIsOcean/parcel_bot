"""Тесты жизненного цикла доставки."""

from datetime import date, timedelta

import pytest

from backend.app.config import settings
from backend.app.services import delivery_service
from backend.app.services.delivery_service import DeliveryError
from shared.models.parcel import Parcel, ParcelSize, ParcelStatus
from shared.models.user import User

SENDER_ID = 1
TRAVELER_ID = 2
STRANGER_ID = 3


async def setup_parcel(session, status=ParcelStatus.ACCEPTED) -> Parcel:
    """Посылка, уже принятая перевозчиком."""
    session.add_all([
        User(id=SENDER_ID, first_name="Отправитель", lang="ru"),
        User(id=TRAVELER_ID, first_name="Перевозчик", lang="ru"),
        User(id=STRANGER_ID, first_name="Посторонний", lang="ru"),
    ])
    parcel = Parcel(
        sender_id=SENDER_ID,
        traveler_id=TRAVELER_ID,
        from_city="Dubai",
        to_city="Almaty",
        description="Документы",
        weight=2.0,
        size=ParcelSize.SMALL,
        price=25.0,
        status=status,
    )
    session.add(parcel)
    await session.commit()
    await session.refresh(parcel)
    return parcel


@pytest.mark.asyncio
async def test_full_happy_path(session):
    """Полный путь: передана, вылет, прилёт, выдача по коду."""
    parcel = await setup_parcel(session)

    parcel = await delivery_service.mark_handed(session, parcel.id, TRAVELER_ID)
    assert parcel.status == ParcelStatus.HANDED
    assert parcel.handed_at is not None
    # Код выдачи появляется вместе с передачей
    assert parcel.handover_code and len(parcel.handover_code) == delivery_service.HANDOVER_CODE_LENGTH
    code = parcel.handover_code

    parcel = await delivery_service.mark_in_transit(session, parcel.id, TRAVELER_ID)
    assert parcel.status == ParcelStatus.IN_TRANSIT

    parcel = await delivery_service.mark_arrived(session, parcel.id, TRAVELER_ID)
    assert parcel.arrived_at is not None
    # Прилёт не меняет статус
    assert parcel.status == ParcelStatus.IN_TRANSIT

    parcel = await delivery_service.mark_delivered(session, parcel.id, TRAVELER_ID, code=code)
    assert parcel.status == ParcelStatus.DELIVERED
    assert parcel.delivered_at is not None


@pytest.mark.asyncio
async def test_wrong_code_rejected(session):
    """Неверный код не закрывает доставку."""
    parcel = await setup_parcel(session)
    await delivery_service.mark_handed(session, parcel.id, TRAVELER_ID)
    await delivery_service.mark_in_transit(session, parcel.id, TRAVELER_ID)

    with pytest.raises(DeliveryError):
        await delivery_service.mark_delivered(session, parcel.id, TRAVELER_ID, code="0000000")

    await session.refresh(parcel)
    assert parcel.status == ParcelStatus.IN_TRANSIT


@pytest.mark.asyncio
async def test_stranger_cannot_move_status(session):
    """Двигать статус может только перевозчик этой посылки."""
    parcel = await setup_parcel(session)
    with pytest.raises(DeliveryError):
        await delivery_service.mark_handed(session, parcel.id, STRANGER_ID)


@pytest.mark.asyncio
async def test_sender_cannot_move_status(session):
    """Отправитель не может отметить передачу за перевозчика."""
    parcel = await setup_parcel(session)
    with pytest.raises(DeliveryError):
        await delivery_service.mark_handed(session, parcel.id, SENDER_ID)


@pytest.mark.asyncio
async def test_wrong_order_rejected(session):
    """Нельзя вылететь, не забрав посылку."""
    parcel = await setup_parcel(session)
    with pytest.raises(DeliveryError):
        await delivery_service.mark_in_transit(session, parcel.id, TRAVELER_ID)


@pytest.mark.asyncio
async def test_arrival_is_idempotent(session):
    """Повторная отметка прилёта не должна ничего ломать."""
    parcel = await setup_parcel(session)
    await delivery_service.mark_handed(session, parcel.id, TRAVELER_ID)
    await delivery_service.mark_in_transit(session, parcel.id, TRAVELER_ID)

    first = await delivery_service.mark_arrived(session, parcel.id, TRAVELER_ID)
    at = first.arrived_at
    second = await delivery_service.mark_arrived(session, parcel.id, TRAVELER_ID)
    assert second.arrived_at == at


@pytest.mark.asyncio
async def test_delivery_builds_reputation(session, monkeypatch):
    """Закрытая доставка увеличивает счётчик и выдаёт галочку на пороге."""
    monkeypatch.setattr(settings, "verified_deliveries_threshold", 1)

    parcel = await setup_parcel(session)
    parcel = await delivery_service.mark_handed(session, parcel.id, TRAVELER_ID)
    code = parcel.handover_code
    await delivery_service.mark_in_transit(session, parcel.id, TRAVELER_ID)
    await delivery_service.mark_delivered(session, parcel.id, TRAVELER_ID, code=code)

    traveler = await session.get(User, TRAVELER_ID)
    assert traveler.deliveries_count == 1
    assert traveler.is_verified is True


@pytest.mark.asyncio
async def test_timeline_shape(session):
    """Таймлайн отдаёт все шаги в фиксированном порядке."""
    parcel = await setup_parcel(session)
    steps = delivery_service.timeline(parcel)
    assert [s["key"] for s in steps] == [
        "created", "accepted", "handed", "in_transit", "arrived", "delivered",
    ]
    # Принято — потому что перевозчик уже назначен
    assert steps[1]["done"] is True
    assert steps[5]["done"] is False


def test_code_is_numeric():
    """Код выдачи диктуется голосом, поэтому только цифры."""
    code = delivery_service.generate_handover_code()
    assert code.isdigit()
    assert len(code) == delivery_service.HANDOVER_CODE_LENGTH
