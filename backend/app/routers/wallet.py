import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import access_service, balance_service, payment_service
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet", tags=["wallet"])
limiter = Limiter(key_func=get_remote_address)


class TopUpRequest(BaseModel):
    """Пополнение баланса."""
    amount_stars: int = Field(gt=0, description="Сумма из разрешённых пакетов")


@router.get("")
async def get_wallet(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Кабинет: баланс, цены и доступные способы пополнения."""
    transactions = await balance_service.history(session, user.id, limit=30)

    return {
        "balance_stars": user.balance_stars or 0,
        # Дневной тариф и состояние сегодняшнего дня
        "access": access_service.access_state(user),
        "packages": settings.topup_packages,
        "star_usd_rate": settings.star_usd_rate,
        # TON показываем только если кошелёк настроен
        "ton_enabled": bool(settings.ton_wallet_address),
        "transactions": [
            {
                "id": t.id,
                "kind": t.kind.value,
                "amount_stars": t.amount_stars,
                "balance_after": t.balance_after,
                "note": t.note,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
    }


@router.post("/day")
async def open_working_day(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Открыть перевозчику сегодняшний рабочий день.

    Списывает дневной тариф, если день ещё не открыт и пробные дни кончились.
    Повторный вызов в тот же день ничего не списывает.
    """
    result = await access_service.open_day(session, user)

    if not result.ok:
        # Денег не хватает — фронт уводит на пополнение
        raise HTTPException(
            status_code=402,
            detail={
                "detail": "insufficient_balance",
                "balance_stars": result.balance,
                "price_stars": settings.daily_fee_stars,
            },
        )

    return {
        "ok": True,
        "reason": result.reason,
        "balance_stars": result.balance,
        "access": access_service.access_state(user),
    }


@router.post("/topup/stars")
@limiter.limit("20/hour")
async def topup_stars(
    request: Request,
    data: TopUpRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Ссылка на счёт Telegram Stars. Открывается в Mini App методом openInvoice."""
    result = await payment_service.create_stars_topup_link(session, user.id, data.amount_stars)

    if not result.ok:
        # Недопустимая сумма — ошибка клиента, всё остальное — сбой Telegram
        status = 400 if result.error == "bad_amount" else 502
        raise HTTPException(status_code=status, detail=result.error)

    return {"invoice_link": result.invoice_link, "payment_id": result.payment_id}


@router.post("/topup/ton")
@limiter.limit("20/hour")
async def topup_ton(
    request: Request,
    data: TopUpRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Реквизиты перевода в TON. Код обязательно указывается в комментарии."""
    result = await payment_service.create_ton_topup(session, user.id, data.amount_stars)

    if not result.ok:
        status = 400 if result.error == "bad_amount" else 503
        raise HTTPException(status_code=status, detail=result.error)

    return {
        "payment_id": result.payment_id,
        "wallet_address": result.wallet_address,
        "amount_ton": result.amount_ton,
        "payment_code": result.payment_code,
        "deep_link": result.deep_link,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
    }


@router.get("/topup/ton/{payment_id}")
async def check_ton_topup(
    payment_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Проверить, дошёл ли перевод в TON."""
    from shared.models.payment import Payment

    payment = await session.get(Payment, payment_id)
    if not payment or payment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Опрашиваем блокчейн по требованию, не дожидаясь фонового цикла
    await payment_service.check_ton_payments(session)
    await session.refresh(payment)

    return {
        "status": payment.status.value,
        "balance_stars": await balance_service.get_balance(session, user.id),
    }
