from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения из .env файла."""

    # Telegram Bot
    bot_token: str = ""
    bot_webhook_url: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./parcel_bot.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # WebApp
    webapp_url: str = ""

    # TON Payments
    ton_wallet_address: str = ""
    ton_api_key: str = ""

    # Subscription prices (USD)
    subscription_monthly_price: float = 40.0
    subscription_quarterly_price: float = 100.0
    subscription_yearly_price: float = 300.0

    # Logging
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Синглтон конфигурации
settings = Settings()

# Проверка безопасности: запрет запуска с дефолтным секретным ключом
if settings.secret_key == "change-me-in-production":
    import warnings
    warnings.warn(
        "SECURITY WARNING: Using default secret_key! "
        "Set SECRET_KEY environment variable in production.",
        stacklevel=1,
    )
