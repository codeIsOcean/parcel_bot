from datetime import datetime
from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    """Обновление профиля."""
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    lang: str | None = Field(default=None, pattern="^(ru|en|kz)$")
    notifications_enabled: bool | None = None


class UserProfile(BaseModel):
    """Полный профиль пользователя."""
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    city: str | None = None
    role: str
    rating: float
    deliveries_count: int
    reviews_count: int
    is_verified: bool
    is_premium: bool
    bio: str | None = None
    avatar_file_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    """Создание отзыва."""
    parcel_id: int
    rating: float = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    """Отзыв в ответе."""
    id: int
    author_id: int
    author_name: str | None = None
    rating: float
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CityResponse(BaseModel):
    """Город в ответе."""
    id: int
    name_en: str
    name_ru: str
    name_kz: str | None = None
    country_code: str
    flag: str

    model_config = {"from_attributes": True}
