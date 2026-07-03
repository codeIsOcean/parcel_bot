import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.users import (
    UserProfile, UserUpdate, ReviewCreate, ReviewResponse,
)
from backend.app.services import user_service
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.user import User
from shared.models.review import Review

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def get_my_profile(user: User = Depends(get_current_user)):
    """Получить свой профиль."""
    return UserProfile.model_validate(user)


@router.put("/me", response_model=UserProfile)
async def update_my_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Обновить свой профиль."""
    updated = await user_service.update_user(
        session, user, **data.model_dump(exclude_none=True),
    )
    return UserProfile.model_validate(updated)


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Получить профиль пользователя."""
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile.model_validate(user)


@router.get("/{user_id}/reviews", response_model=list[ReviewResponse])
async def get_user_reviews(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Получить отзывы о пользователе."""
    reviews, _ = await user_service.get_user_reviews(
        session, user_id, page=page, limit=limit,
    )
    return [ReviewResponse(**r) for r in reviews]


@router.post("/{user_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    user_id: int,
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Оставить отзыв о пользователе."""
    # Нельзя оставить отзыв себе
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot review yourself")

    # Проверяем что пользователь существует
    target = await user_service.get_user_by_id(session, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем что посылка существует и доставлена
    parcel = (await session.execute(
        select(Parcel).where(Parcel.id == data.parcel_id)
    )).scalar_one_or_none()
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")
    if parcel.status != ParcelStatus.DELIVERED:
        raise HTTPException(status_code=400, detail="Parcel must be delivered before review")

    # Проверяем что пользователь — участник посылки (отправитель или перевозчик)
    if user.id not in (parcel.sender_id, parcel.traveler_id):
        raise HTTPException(status_code=403, detail="You are not a participant of this parcel")

    # Проверяем что target — другой участник посылки (нельзя оставить отзыв не тому)
    if user_id not in (parcel.sender_id, parcel.traveler_id):
        raise HTTPException(status_code=400, detail="Target user is not a participant of this parcel")

    # Проверяем что нет дубликата — один отзыв на посылку от одного автора
    existing = (await session.execute(
        select(Review).where(and_(
            Review.author_id == user.id,
            Review.parcel_id == data.parcel_id,
        ))
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="You already reviewed this parcel")

    logger.info("[RATING] Отзыв: author=%s, target=%s, rating=%s", user.id, user_id, data.rating)

    # Создаём отзыв
    review = Review(
        author_id=user.id,
        target_id=user_id,
        parcel_id=data.parcel_id,
        rating=data.rating,
        comment=data.comment,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)

    # Пересчитываем средний рейтинг
    await user_service.recalculate_rating(session, user_id)

    return ReviewResponse(
        id=review.id,
        author_id=review.author_id,
        author_name=user.full_name,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
    )


