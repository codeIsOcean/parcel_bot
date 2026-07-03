from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Запрос на авторизацию через Telegram initData."""
    init_data: str


class RefreshRequest(BaseModel):
    """Запрос на обновление JWT токена."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Ответ с JWT токенами."""
    token: str
    refresh_token: str
    user: "UserResponse"


class UserResponse(BaseModel):
    """Данные пользователя в ответе."""
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    role: str
    rating: float
    deliveries_count: int
    reviews_count: int
    is_verified: bool
    lang: str
    avatar_file_id: str | None = None

    model_config = {"from_attributes": True}


# Обновляем forward reference
TokenResponse.model_rebuild()
