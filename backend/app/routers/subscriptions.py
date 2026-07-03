import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import subscription_service
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SubscriptionCreate(BaseModel):
    """Запрос на создание подписки."""
    plan: str  # monthly, quarterly, yearly
    payment_method: str  # stars, ton
    transaction_id: str | None = None


class SubscriptionResponse(BaseModel):
    """Ответ с данными подписки."""
    id: int
    plan: str
    starts_at: str
    expires_at: str
    price: float
    payment_method: str

    model_config = {"from_attributes": True}


@router.get("/active")
async def get_active_subscription(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить активную подписку."""
    sub = await subscription_service.get_active_subscription(session, user.id)
    if not sub:
        return {"active": False}

    return {
        "active": True,
        "plan": sub.plan.value,
        "expires_at": sub.expires_at.isoformat(),
        "price": sub.price,
    }


@router.post("", status_code=201)
async def create_subscription(
    data: SubscriptionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Создать подписку (после подтверждения оплаты)."""
    # Определяем цену по плану
    prices = {
        "monthly": settings.subscription_monthly_price,
        "quarterly": settings.subscription_quarterly_price,
        "yearly": settings.subscription_yearly_price,
    }
    price = prices.get(data.plan)
    if price is None:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Платные подписки требуют transaction_id для верификации
    if price > 0 and not data.transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id is required for paid plans")

    try:
        sub = await subscription_service.create_subscription(
            session,
            user_id=user.id,
            plan=data.plan,
            payment_method=data.payment_method,
            price=price,
            transaction_id=data.transaction_id,
        )
        return {
            "id": sub.id,
            "plan": sub.plan.value,
            "expires_at": sub.expires_at.isoformat(),
            "price": sub.price,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
async def get_subscription_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Получить историю подписок."""
    subs = await subscription_service.get_subscription_history(session, user.id)
    return [
        {
            "id": s.id,
            "plan": s.plan.value,
            "starts_at": s.starts_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "price": s.price,
            "payment_method": s.payment_method,
        }
        for s in subs
    ]


@router.get("/prices")
async def get_subscription_prices():
    """Получить цены подписок."""
    return {
        "monthly": settings.subscription_monthly_price,
        "quarterly": settings.subscription_quarterly_price,
        "yearly": settings.subscription_yearly_price,
    }
