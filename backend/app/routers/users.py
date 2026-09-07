import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.schemas.users import (
    PrivateProfile, UserProfile, UserUpdate, ReviewCreate, ReviewReply, ReviewResponse,
)
from backend.app.services import user_service
from backend.app.services.admin_service import is_admin
from backend.app.services.user_service import ReviewReplyError
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.user import User, UserRole
from shared.models.review import Review

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _private(user: User) -> PrivateProfile:
    """Свой профиль с приватными полями и признаком администратора."""
    profile = PrivateProfile.model_validate(user)
    profile.is_admin = is_admin(user)
    return profile


@router.get("/me", response_model=PrivateProfile)
async def get_my_profile(user: User = Depends(get_current_user)):
    """Получить свой профиль."""
    return _private(user)


@router.put("/me", response_model=PrivateProfile)
async def update_my_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Обновить свой профиль."""
    fields = data.model_dump(exclude_none=True)
    # Режим хранится в enum роли
    if "role" in fields:
        fields["role"] = UserRole(fields["role"])
    updated = await user_service.update_user(session, user, **fields)
    return _private(updated)


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: int,
    _: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
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
        tags=user_service.normalize_tags(data.tags),
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
        target_id=review.target_id,
        rating=review.rating,
        comment=review.comment,
        tags=review.tag_list,
        created_at=review.created_at,
    )


@router.post("/reviews/{review_id}/reply", response_model=ReviewResponse)
async def reply_to_review(
    review_id: int,
    data: ReviewReply,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Ответить на отзыв о себе. Один ответ, только получатель отзыва."""
    try:
        review = await user_service.reply_to_review(session, review_id, user.id, data.text)
    except ReviewReplyError as e:
        # Причина — в теле ответа, фронт показывает подходящий текст
        status = {"not_found": 404, "not_target": 403, "already_replied": 409}[e.reason]
        raise HTTPException(status_code=status, detail=e.reason)

    author = await user_service.get_user_by_id(session, review.author_id)
    return ReviewResponse(
        id=review.id,
        author_id=review.author_id,
        author_name=author.full_name if author else None,
        target_id=review.target_id,
        rating=review.rating,
        comment=review.comment,
        tags=review.tag_list,
        reply_text=review.reply_text,
        reply_created_at=review.reply_created_at,
        created_at=review.created_at,
    )


