"""Защитные механизмы: экранирование HTML, перебор кода выдачи, проверка файлов."""

from datetime import date, timedelta

import pytest

from backend.app.services import delivery_service, media_service
from backend.app.services.delivery_service import DeliveryError
from backend.app.services.media_service import MediaError
from shared.locale.notify_texts import nt
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.user import User


def test_notify_texts_escape_user_input():
    """Имя с тегом не ломает и не подменяет HTML-уведомление."""
    text = nt("ru", "new_message", sender_name='<a href="https://evil">Вася</a>', text="<b>hi</b>")
    assert "<a href" not in text and "&lt;a href" in text
    assert "<b>hi</b>" not in text
    # Разметка самого шаблона остаётся
    assert "<b>" in text


def test_media_rejects_fake_image():
    """Файл с заголовком image/png, но не PNG внутри, не сохраняется."""
    with pytest.raises(MediaError):
        media_service.save_bytes(b"<?php evil ?>", "image/png", subdir="t")
    # Настоящая PNG-сигнатура проходит
    path = media_service.save_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32, "image/png", subdir="t")
    assert path.endswith(".png")


def test_upload_quota():
    """Дневная квота на загрузки."""
    media_service._uploads_today.clear()
    for _ in range(media_service.MAX_UPLOADS_PER_DAY):
        media_service.check_upload_quota(42)
    with pytest.raises(MediaError):
        media_service.check_upload_quota(42)


@pytest.mark.asyncio
async def test_handover_code_lockout(session):
    """Пять неверных кодов закрывают ввод — перебор невозможен."""
    session.add_all([User(id=1, first_name="S"), User(id=2, first_name="T")])
    parcel = Parcel(sender_id=1, traveler_id=2, from_city="Dubai", to_city="Almaty", description="Док",
                    weight=1, price=10, status=ParcelStatus.IN_TRANSIT, handover_code="123456")
    session.add(parcel)
    await session.commit()
    assert len(delivery_service.generate_handover_code()) == 6

    for _ in range(delivery_service.MAX_HANDOVER_ATTEMPTS - 1):
        with pytest.raises(DeliveryError, match="Invalid"):
            await delivery_service.mark_delivered(session, parcel.id, 2, "000000")
    with pytest.raises(DeliveryError, match="handover_locked"):
        await delivery_service.mark_delivered(session, parcel.id, 2, "000000")
    # Даже верный код после блокировки не проходит
    with pytest.raises(DeliveryError, match="handover_locked"):
        await delivery_service.mark_delivered(session, parcel.id, 2, "123456")
