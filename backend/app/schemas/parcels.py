from datetime import datetime
from pydantic import BaseModel, Field


class ParcelCreate(BaseModel):
    """Создание посылки."""
    from_city: str = Field(min_length=1, max_length=100)
    to_city: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=3, max_length=1000)
    weight: float = Field(gt=0, le=50)
    size: str = Field(default="medium")
    price: float = Field(gt=0, le=10000)
    traveler_id: int | None = None


class ParcelResponse(BaseModel):
    """Посылка в ответе."""
    id: int
    sender_id: int
    traveler_id: int | None = None
    from_city: str
    to_city: str
    description: str
    weight: float
    size: str
    price: float
    accepted_price: float | None = None
    status: str
    photo_file_ids: str | None = None
    created_at: datetime
    # Этапы доставки
    handed_at: datetime | None = None
    in_transit_at: datetime | None = None
    arrived_at: datetime | None = None
    delivered_at: datetime | None = None
    # Данные перевозчика (заполняются при наличии traveler_id)
    traveler_name: str | None = None
    traveler_rating: float | None = None

    model_config = {"from_attributes": True}


class PaginatedParcels(BaseModel):
    """Список посылок с пагинацией."""
    items: list[ParcelResponse]
    total: int
    page: int
    limit: int


class DeliveryStepRequest(BaseModel):
    """Отметка этапа доставки перевозчиком."""
    # Фото при передаче или выдаче — file_id из Telegram через запятую
    photo_file_ids: str | None = Field(default=None, max_length=2000)


class DeliveryConfirmRequest(DeliveryStepRequest):
    """Закрытие доставки кодом, который назвал получатель."""
    code: str = Field(min_length=3, max_length=8)
