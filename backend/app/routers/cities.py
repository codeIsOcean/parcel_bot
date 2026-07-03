import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.schemas.users import CityResponse
from shared.models.city import City

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=list[CityResponse])
async def get_cities(session: AsyncSession = Depends(get_session)):
    """Получить список активных городов."""
    result = await session.execute(
        select(City).where(City.is_active == True).order_by(City.sort_order)
    )
    cities = result.scalars().all()
    return [CityResponse.model_validate(c) for c in cities]
