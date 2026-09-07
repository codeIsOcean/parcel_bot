"""Защита от мошенничества и запрещённых вложений.

Две линии обороны. Первая — проверка описания посылки на запрещённое
вложение при создании: перевозчик рискует на границе, поэтому список
жёсткий. Вторая — жалобы участников: при накоплении жалоб доступ
закрывается автоматически, не дожидаясь ручного разбора.
"""

import logging

from backend.app.config import settings
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.parcel import Parcel
from shared.models.report import Report, ReportReason, ReportStatus
from shared.models.user import User

logger = logging.getLogger(__name__)

# Сколько подтверждённых жалоб закрывают доступ автоматически
AUTO_BLOCK_THRESHOLD = 3

# Запрещённые вложения. Список намеренно узкий: ловим то, за что перевозчик
# получит реальные проблемы на таможне, а не всё подряд.
PROHIBITED_TERMS: tuple[str, ...] = (
    # Наркотики
    "наркотик", "марихуан", "гашиш", "кокаин", "героин", "мефедрон", "амфетамин",
    "drug", "cocaine", "heroin", "cannabis", "marijuana",
    # Оружие и боеприпасы
    "оружие", "пистолет", "автомат", "патрон", "боеприпас", "глушител",
    "weapon", "gun", "pistol", "ammo", "ammunition",
    # Взрывчатка и яды
    "взрывчат", "тротил", "динамит", "яд ", "отрав",
    "explosive", "dynamite", "poison",
    # Наличные и документы на предъявителя
    "наличк", "наличны", "cash",
)


class ProhibitedContentError(Exception):
    """В описании посылки найдено запрещённое вложение."""

    def __init__(self, terms: list[str]):
        self.terms = terms
        super().__init__("Prohibited content: " + ", ".join(terms))


def find_prohibited(text: str) -> list[str]:
    """Найти в тексте признаки запрещённого вложения."""
    if not text:
        return []

    # Сравниваем в нижнем регистре, буква ё приводится к е
    normalized = text.lower().replace("ё", "е")
    return [term.strip() for term in PROHIBITED_TERMS if term in normalized]


def ensure_allowed(text: str) -> None:
    """Бросить ProhibitedContentError, если описание содержит запрещённое."""
    terms = find_prohibited(text)
    if terms:
        logger.warning("[MODERATION] Запрещённое вложение: %s", terms)
        raise ProhibitedContentError(terms)


async def create_report(
    session: AsyncSession,
    author: User,
    target_id: int,
    reason: str,
    comment: str | None = None,
    parcel_id: int | None = None,
) -> Report:
    """Принять жалобу на пользователя."""
    # На себя жаловаться бессмысленно
    if author.id == target_id:
        raise ValueError("Cannot report yourself")

    target = await session.get(User, target_id)
    if not target:
        raise ValueError("User not found")

    try:
        reason_enum = ReportReason(reason)
    except ValueError:
        raise ValueError(f"Invalid reason: {reason}")

    # Жалоба привязана к сделке: обе стороны должны быть её участниками.
    # Иначе любой аккаунт мог бы «нажаловаться» на кого угодно по чужим id.
    if not parcel_id:
        raise ValueError("Report must reference a parcel")
    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        raise ValueError("Parcel not found")
    participants = {parcel.sender_id, parcel.traveler_id}
    if author.id not in participants or target_id not in participants:
        raise ValueError("Both users must be participants of this parcel")

    # Одна жалоба от одного автора на одного пользователя в рамках одной посылки
    duplicate = (await session.execute(
        select(Report).where(
            Report.author_id == author.id,
            Report.target_id == target_id,
            Report.parcel_id == parcel_id,
        )
    )).scalar_one_or_none()
    if duplicate:
        raise ValueError("You already reported this user for this parcel")

    report = Report(
        author_id=author.id,
        target_id=target_id,
        parcel_id=parcel_id,
        reason=reason_enum,
        comment=comment,
        status=ReportStatus.OPEN,
    )
    session.add(report)

    # Счётчик жалоб на пользователе — быстрый признак для выдачи и модерации
    target.reports_count = (target.reports_count or 0) + 1

    await session.flush()

    # Порог считаем по РАЗНЫМ авторам открытых/подтверждённых жалоб, чтобы один
    # человек не смог заблокировать другого серией жалоб. Администраторов
    # автоблокировка не касается — их разбирают вручную.
    distinct_authors = (await session.execute(
        select(func.count(func.distinct(Report.author_id))).where(
            Report.target_id == target_id,
            Report.status != ReportStatus.REVIEWED,
        )
    )).scalar() or 0
    if (
        distinct_authors >= AUTO_BLOCK_THRESHOLD
        and not target.is_blocked
        and not target.is_admin
        and target.id not in settings.admin_id_list
    ):
        target.is_blocked = True
        logger.warning(
            "[MODERATION] Автоблокировка: user=%s, авторов жалоб=%s", target_id, distinct_authors,
        )

    await session.commit()
    await session.refresh(report)

    logger.info("[MODERATION] Жалоба: author=%s, target=%s, reason=%s", author.id, target_id, reason)
    return report


async def get_reports_about(session: AsyncSession, target_id: int) -> list[Report]:
    """Жалобы на пользователя — для будущей панели модерации."""
    return list((await session.execute(
        select(Report)
        .where(Report.target_id == target_id)
        .order_by(Report.created_at.desc())
    )).scalars().all())
