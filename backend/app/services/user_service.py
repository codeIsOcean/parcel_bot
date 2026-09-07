from datetime import datetime, timezone
import logging

from backend.app.config import settings
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services import notification_service
from shared.models.user import User, UserRole
from shared.models.review import Review

logger = logging.getLogger(__name__)


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    last_name: str | None = None,
    username: str | None = None,
    language_code: str | None = None,
    is_premium: bool = False,
) -> tuple[User, bool]:
    """Получить или создать пользователя по Telegram ID."""
    # Ищем существующего
    result = await session.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        # Обновляем данные из Telegram (имя могло измениться)
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.is_premium = is_premium
        user.bot_blocked = False  # Раз зашёл — бот не заблокирован
        await session.commit()
        return user, False

    # Создаём нового пользователя
    logger.info("[AUTH] Новый пользователь: tg_id=%s, name=%s", telegram_id, first_name)
    user = User(
        id=telegram_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        lang=language_code if language_code in ("ru", "en", "kz") else "ru",
        is_premium=is_premium,
        role=UserRole.SENDER,
        # Пробные дни выдаются один раз при регистрации
        trial_days_left=settings.trial_active_days,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user, True


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Получить пользователя по ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(session: AsyncSession, user: User, **kwargs) -> User:
    """Обновить данные пользователя."""
    for key, value in kwargs.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    logger.info("[USER] Профиль обновлён: user=%s", user.id)
    return user


async def recalculate_rating(session: AsyncSession, user_id: int) -> float:
    """Пересчитать средний рейтинг пользователя."""
    result = await session.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.target_id == user_id)
    )
    row = result.one()
    avg_rating = float(row[0] or 0)
    reviews_count = int(row[1] or 0)

    # Обновляем пользователя
    user = await get_user_by_id(session, user_id)
    if user:
        user.rating = round(avg_rating, 2)
        user.reviews_count = reviews_count
        await session.commit()

    return avg_rating


async def get_user_reviews(
    session: AsyncSession,
    user_id: int,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """Получить отзывы о пользователе."""
    # Запрос с данными автора
    query = (
        select(Review, User)
        .join(User, Review.author_id == User.id)
        .where(Review.target_id == user_id)
        .order_by(Review.created_at.desc())
    )

    # Считаем количество
    count_q = select(func.count()).select_from(
        select(Review.id).where(Review.target_id == user_id).subquery()
    )
    total = (await session.execute(count_q)).scalar() or 0

    # Пагинация
    query = query.offset((page - 1) * limit).limit(limit)
    result = await session.execute(query)
    rows = result.all()

    reviews = []
    for review, author in rows:
        reviews.append({
            "id": review.id,
            "author_id": review.author_id,
            "author_name": author.full_name,
            "target_id": review.target_id,
            "rating": review.rating,
            "comment": review.comment,
            "tags": review.tag_list,
            "reply_text": review.reply_text,
            "reply_created_at": review.reply_created_at,
            "created_at": review.created_at,
        })

    return reviews, total


# Разрешённые теги-похвалы в отзыве
REVIEW_TAGS = ("on_time", "careful", "polite", "good_price", "recommended")


def normalize_tags(tags: list[str] | None) -> str | None:
    """Оставить только известные теги, без дублей, в строку для хранения."""
    if not tags:
        return None
    clean = [t for t in dict.fromkeys(tags) if t in REVIEW_TAGS]
    return ",".join(clean) or None


class ReviewReplyError(Exception):
    """Ответить на отзыв нельзя: причина в reason."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


async def reply_to_review(session: AsyncSession, review_id: int, actor_id: int, text: str) -> Review:
    """Ответ получателя на отзыв. Один ответ, только от того, кому отзыв."""
    review = await session.get(Review, review_id)
    if not review:
        raise ReviewReplyError("not_found")
    if review.target_id != actor_id:
        raise ReviewReplyError("not_target")
    if review.reply_text:
        raise ReviewReplyError("already_replied")

    review.reply_text = text.strip()
    review.reply_created_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(review)

    # Автор отзыва узнаёт об ответе
    author = await get_user_by_id(session, review.author_id)
    target = await get_user_by_id(session, actor_id)
    if author and target:
        notification_service.notify_review_replied(author, target, review.reply_text)

    logger.info("[RATING] Ответ на отзыв: review=%s, by=%s", review_id, actor_id)
    return review
