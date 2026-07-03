import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_session
from shared.models.user import User

logger = logging.getLogger(__name__)

# Bearer token схема
security = HTTPBearer(auto_error=False)


def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Верифицирует initData от Telegram WebApp.
    Проверяет HMAC-SHA256 подпись.
    Возвращает данные пользователя или None при невалидности.
    """
    try:
        # Парсим query string
        parsed = parse_qs(init_data, keep_blank_values=True)

        # Извлекаем hash
        received_hash = parsed.pop("hash", [None])[0]
        if not received_hash:
            return None

        # Формируем строку для проверки (отсортированные ключи)
        data_check_string = "\n".join(
            f"{k}={v[0]}" for k, v in sorted(parsed.items())
        )

        # HMAC-SHA256: secret = HMAC("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            settings.bot_token.encode(),
            hashlib.sha256,
        ).digest()

        # Вычисляем hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Сравниваем (constant-time)
        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        # Проверяем auth_date — отклоняем данные старше 1 часа (рекомендация Telegram)
        auth_date_str = parsed.get("auth_date", [None])[0]
        if auth_date_str:
            auth_date = int(auth_date_str)
            now = int(datetime.now(timezone.utc).timestamp())
            if now - auth_date > 3600:
                logger.warning("[AUTH] initData устарели: auth_date=%s, now=%s", auth_date, now)
                return None

        return parsed
    except Exception as e:
        logger.error("[AUTH] Ошибка верификации initData: %s", e)
        return None


def create_access_token(user_id: int) -> str:
    """Создать JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int) -> str:
    """Создать JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependency — получить текущего авторизованного пользователя.
    Извлекает user_id из JWT, загружает из БД.
    """
    # Проверяем наличие токена
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        # Декодируем JWT
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        # Проверяем что это access token, а не refresh
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Загружаем пользователя из БД
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
