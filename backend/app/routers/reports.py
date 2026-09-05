import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import moderation_service
from shared.models.report import ReportReason
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])
limiter = Limiter(key_func=get_remote_address)


class ReportCreate(BaseModel):
    """Жалоба на пользователя."""
    target_id: int
    reason: str = Field(description="scam / no_show / prohibited / rude / other")
    comment: str | None = Field(default=None, max_length=1000)
    parcel_id: int | None = None


@router.get("/reasons")
async def get_reasons():
    """Список причин жалобы для формы."""
    # Тексты причин фронт берёт из своей локали по ключу
    return {"items": [r.value for r in ReportReason]}


@router.post("", status_code=201)
@limiter.limit("5/hour")
async def create_report(
    request: Request,
    data: ReportCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Пожаловаться на пользователя."""
    try:
        report = await moderation_service.create_report(
            session,
            author=user,
            target_id=data.target_id,
            reason=data.reason,
            comment=data.comment,
            parcel_id=data.parcel_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"id": report.id, "status": report.status.value}
