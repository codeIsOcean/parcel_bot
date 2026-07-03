import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
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
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at,
        })

    return reviews, total
