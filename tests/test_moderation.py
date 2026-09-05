"""Тесты защиты от запрещённых вложений и жалоб."""

import pytest

from backend.app.services import moderation_service
from backend.app.services.moderation_service import ProhibitedContentError
from shared.models.user import User


async def add_user(session, user_id: int) -> User:
    """Создать пользователя."""
    user = User(id=user_id, first_name=f"User{user_id}", lang="ru")
    session.add(user)
    await session.commit()
    return user


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
    """Жалоба увеличивает счётчик у нарушителя."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)

    await moderation_service.create_report(session, author, target.id, "scam")

    await session.refresh(target)
    assert target.reports_count == 1
    assert target.is_blocked is False


@pytest.mark.asyncio
async def test_auto_block_after_threshold(session):
    """При наборе порога жалоб доступ закрывается автоматически."""
    target = await add_user(session, 99)
    for i in range(moderation_service.AUTO_BLOCK_THRESHOLD):
        author = await add_user(session, 100 + i)
        # Разные посылки, чтобы не сработала защита от дублей
        await moderation_service.create_report(
            session, author, target.id, "scam", parcel_id=None if i == 0 else None,
        )

    await session.refresh(target)
    assert target.reports_count == moderation_service.AUTO_BLOCK_THRESHOLD
    assert target.is_blocked is True


@pytest.mark.asyncio
async def test_duplicate_report_rejected(session):
    """Один автор не может жаловаться дважды по одной посылке."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)

    await moderation_service.create_report(session, author, target.id, "rude")
    with pytest.raises(ValueError):
        await moderation_service.create_report(session, author, target.id, "rude")


@pytest.mark.asyncio
async def test_cannot_report_self(session):
    """На себя пожаловаться нельзя."""
    author = await add_user(session, 1)
    with pytest.raises(ValueError):
        await moderation_service.create_report(session, author, author.id, "other")


@pytest.mark.asyncio
async def test_invalid_reason_rejected(session):
    """Неизвестная причина не принимается."""
    author = await add_user(session, 1)
    target = await add_user(session, 2)
    with pytest.raises(ValueError):
        await moderation_service.create_report(session, author, target.id, "нет-такой-причины")
