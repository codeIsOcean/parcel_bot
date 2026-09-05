"""Ответ оператора из KVD Ads Panel пользователю (внутренний эндпоинт).

Панель — не Telegram-клиент, JWT у неё нет, поэтому вход по общему секрету
CRM_API_KEY в заголовке X-API-Key: тем же ключом мы подписываем исходящие
сообщения в crm_bridge. Ответ идёт через тот же support_service, что и ответ
администратора из бота: ложится в переписку, пользователь получает пуш.
Обратно в CRM не зеркалится (origin="crm") — петли нет.
"""

import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_session
from backend.app.services import support_service
from backend.app.services.support_service import ORIGIN_CRM

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/crm", tags=["internal-crm"])


class CrmReply(BaseModel):
    """Ответ оператора пользователю."""
    user_id: int
    text: str = Field(min_length=1, max_length=4000)


async def require_crm_key(x_api_key: str | None = Header(None)) -> None:
    """Пускает только с верным CRM_API_KEY. Ключ не задан → эндпоинта как будто нет."""
    key = settings.crm_api_key.strip()
    if not key:
        raise HTTPException(status_code=404, detail="Not found")
    # Сравнение за постоянное время — без утечки по таймингу
    if not x_api_key or not hmac.compare_digest(x_api_key, key):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/reply", dependencies=[Depends(require_crm_key)])
async def crm_reply(data: CrmReply, session: AsyncSession = Depends(get_session)) -> dict:
    """Оператор из панели отвечает пользователю user_id."""
    message = await support_service.send_admin_reply(
        session, support_service.primary_admin_id(), data.user_id, data.text, origin=ORIGIN_CRM,
    )
    # Пользователь не обращался — отвечать некуда
    if message is None:
        raise HTTPException(status_code=404, detail="Пользователь не обращался в поддержку")

    logger.info("[CRM] Ответ из панели пользователю %s, сообщение %s", data.user_id, message.id)
    return {"ok": True, "message_id": message.id, "session_id": message.session_id}
