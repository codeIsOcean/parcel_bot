import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import support_service
from backend.app.services.support_service import SupportUnavailable
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/support", tags=["support"])
limiter = Limiter(key_func=get_remote_address)


class SupportSend(BaseModel):
    """Сообщение в поддержку."""
    text: str = Field(min_length=1, max_length=2000)


@router.get("/messages")
async def get_support_messages(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Переписка с поддержкой."""
    messages = await support_service.get_messages(session, user.id)

    return {
        "items": [
            {
                "id": m.id,
                "role": m.sender_role,
                "text": m.text,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        # Настроена ли поддержка вообще (администраторы в Telegram или CRM-панель)
        "available": support_service.is_available(),
    }


@router.get("/unread")
async def get_unread(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Сколько ответов поддержки пользователь ещё не прочитал."""
    return {"unread": await support_service.unread_for_user(session, user.id)}


@router.post("/messages", status_code=201)
@limiter.limit("20/hour")
async def send_support_message(
    request: Request,
    data: SupportSend,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Написать в поддержку."""
    try:
        message = await support_service.send_user_message(session, user, data.text)
    except SupportUnavailable:
        # Администраторы не заданы — честно говорим, что писать некому
        raise HTTPException(status_code=503, detail="support_unavailable")

    return {
        "id": message.id,
        "role": message.sender_role,
        "text": message.text,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }
