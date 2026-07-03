from datetime import date, datetime
from pydantic import BaseModel, Field


class FlightCreate(BaseModel):
    """Создание рейса."""
    from_city: str = Field(min_length=1, max_length=100)
    to_city: str = Field(min_length=1, max_length=100)
    flight_date: date
    flight_number: str | None = Field(default=None, max_length=20)
    available_kg: float = Field(gt=0, le=100)
    price_per_kg: float = Field(gt=0, le=1000)
    notes: str | None = Field(default=None, max_length=500)


class FlightResponse(BaseModel):
    """Рейс в ответе."""
    id: int
    traveler_id: int
    from_city: str
    to_city: str
    flight_date: date
    flight_number: str | None = None
    available_kg: float
    total_kg: float
    price_per_kg: float
    notes: str | None = None
    status: str
    requests_count: int
    created_at: datetime

    # Данные перевозчика (для поиска)
    traveler_name: str | None = None
    traveler_rating: float | None = None
    traveler_trips: int | None = None
    traveler_verified: bool | None = None

    model_config = {"from_attributes": True}


class PaginatedFlights(BaseModel):
    """Список рейсов с пагинацией."""
    items: list[FlightResponse]
    total: int
    page: int
    limit: int
