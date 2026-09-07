"""Тесты защиты от запрещённых вложений и жалоб."""

import pytest

from backend.app.services import moderation_service
from backend.app.services.moderation_service import ProhibitedContentError
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.user import User


async def add_user(session, user_id: int, **fields) -> User:
    """Создать пользователя."""
    user = User(id=user_id, first_name=f"User{user_id}", lang="ru", **fields)
    session.add(user)
    await session.commit()
    return user


async def add_deal(session, sender_id: int, traveler_id: int) -> Parcel:
    """Посылка, где оба — участники сделки (жалоба возможна только по ней)."""
    parcel = Parcel(sender_id=sender_id, traveler_id=traveler_id, from_city="Dubai", to_city="Almaty",
                    description="Док", weight=1, price=10, status=ParcelStatus.DELIVERED)
    session.add(parcel)
    await session.commit()
    await session.refresh(parcel)
    return parcel


def test_detects_prohibited_words():
    """Явно запрещённое вложение находится в описании."""
    assert moderation_service.find_prohibited("Везу немного наркотиков")
    assert moderation_service.find_prohibited("weapon parts")


def test_detects_regardless_of_case_and_yo():
    """Регистр и буква ё не должны обходить проверку."""
    assert moderation_service.find_prohibited("ОРУЖИЕ в коробке")


def test_allows_normal_parcel():
    """Обычная посылка проходит без замечаний."""
    assert moderation_service.find_prohibited("Документы и детская одежда") == []
    moderation_service.ensure_allowed("Ноутбук в коробке")


def test_ensure_allowed_raises():
    """Запрещённое вложение останавливает создание посылки."""
    with pytest.raises(ProhibitedContentError) as exc:
        moderation_service.ensure_allowed("тут кокаин")
    assert exc.value.terms


@pytest.mark.asyncio
async def test_report_increments_counter(session):
    """Жалоба по своей сделке увеличивает счётчик у нарушителя."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)
    deal = await add_deal(session, author.id, target.id)

    await moderation_service.create_report(session, author, target.id, "scam", parcel_id=deal.id)

    await session.refresh(target)
    assert target.reports_count == 1
    assert target.is_blocked is False


@pytest.mark.asyncio
async def test_report_requires_participation(session):
    """Жаловаться можно только на вторую сторону своей сделки."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)
    stranger = await add_user(session, 3)
    deal = await add_deal(session, stranger.id, target.id)

    # Без посылки — нельзя
    with pytest.raises(ValueError):
        await moderation_service.create_report(session, author, target.id, "scam")
    # Чужая сделка — нельзя
    with pytest.raises(ValueError):
        await moderation_service.create_report(session, author, target.id, "scam", parcel_id=deal.id)
    await session.refresh(target)
    assert target.reports_count == 0


@pytest.mark.asyncio
async def test_auto_block_after_threshold(session):
    """Порог — жалобы от разных людей, каждая по своей сделке."""
    target = await add_user(session, 99)
    for i in range(moderation_service.AUTO_BLOCK_THRESHOLD):
        author = await add_user(session, 100 + i)
        deal = await add_deal(session, author.id, target.id)
        await moderation_service.create_report(session, author, target.id, "no_show", parcel_id=deal.id)

    await session.refresh(target)
    assert target.is_blocked is True


@pytest.mark.asyncio
async def test_one_author_cannot_block_alone(session):
    """Один человек серией жалоб по разным посылкам никого не блокирует."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)
    for _ in range(moderation_service.AUTO_BLOCK_THRESHOLD + 1):
        deal = await add_deal(session, author.id, target.id)
        await moderation_service.create_report(session, author, target.id, "rude", parcel_id=deal.id)

    await session.refresh(target)
    assert target.reports_count == moderation_service.AUTO_BLOCK_THRESHOLD + 1
    assert target.is_blocked is False


@pytest.mark.asyncio
async def test_admin_never_auto_blocked(session):
    """Администратора автоблокировка не касается."""
    target = await add_user(session, 99, is_admin=True)
    for i in range(moderation_service.AUTO_BLOCK_THRESHOLD):
        author = await add_user(session, 100 + i)
        deal = await add_deal(session, author.id, target.id)
        await moderation_service.create_report(session, author, target.id, "scam", parcel_id=deal.id)

    await session.refresh(target)
    assert target.is_blocked is False


@pytest.mark.asyncio
async def test_duplicate_report_rejected(session):
    """Повторная жалоба по той же посылке отклоняется."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)
    deal = await add_deal(session, author.id, target.id)

    await moderation_service.create_report(session, author, target.id, "scam", parcel_id=deal.id)
    with pytest.raises(ValueError):
        await moderation_service.create_report(session, author, target.id, "scam", parcel_id=deal.id)
