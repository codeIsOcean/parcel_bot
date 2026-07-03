import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_telegram_init_data,
)
from backend.app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from backend.app.services import user_service
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Авторизация через Telegram initData → JWT."""
    logger.info("[AUTH] Попытка авторизации")

    # Верифицируем подпись Telegram
    parsed = verify_telegram_init_data(data.init_data)
    if not parsed:
        raise HTTPException(status_code=401, detail="Invalid Telegram data")

    # Парсим данные пользователя из initData
    user_data = json.loads(parsed.get("user", ["{}"])[0])
    if not user_data.get("id"):
        raise HTTPException(status_code=401, detail="No user data in initData")

    # Получаем или создаём пользователя
    user, created = await user_service.get_or_create_user(
        session,
        telegram_id=user_data["id"],
        first_name=user_data.get("first_name", "User"),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        is_premium=user_data.get("is_premium", False),
    )

    # Генерируем JWT токены
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    logger.info("[AUTH] Авторизован: user=%s, new=%s", user.id, created)

    return TokenResponse(
        token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Обновить JWT access token по refresh token."""
    from jose import JWTError, jwt as jose_jwt
    from backend.app.config import settings as app_settings

    try:
        # Декодируем refresh token
        payload = jose_jwt.decode(
            data.refresh_token,
            app_settings.secret_key,
            algorithms=[app_settings.jwt_algorithm],
        )

        # Проверяем тип — только refresh
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Загружаем пользователя из БД
    user = await user_service.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Генерируем новые токены
    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)

    logger.info("[AUTH] Token refreshed: user=%s", user.id)

    return TokenResponse(
        token=new_access,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Получить данные текущего пользователя."""
    return UserResponse.model_validate(user)
