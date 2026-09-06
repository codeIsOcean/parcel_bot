from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения из .env файла."""

    # Telegram Bot
    bot_token: str = ""
    bot_webhook_url: str = ""

    # Режим получения апдейтов. Polling оставлен как запасной вариант:
    # на одном токене одновременно может работать только один процесс.
    use_webhook: bool = False
    webhook_path: str = "/webhook"
    webhook_port: int = 8081
    # Секрет, которым Telegram подписывает каждый запрос к вебхуку
    webhook_secret: str = ""

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

    # Юзернейм бота без @ — нужен для ссылок в объявлениях по чатам
    bot_username: str = ""

    # ID администраторов через запятую: кто может подключать чаты к рассылке
    admin_ids: str = ""

    # === CRM — мост чата поддержки в KVD Ads Panel ===
    # Копии сообщений поддержки уходят в POST crm_ingest_url (X-API-Key), ответы
    # оператора из панели приходят на /api/v1/internal/crm/reply тем же ключом.
    # Оба пустые → мост выключен, ничего никуда не шлётся.
    crm_ingest_url: str = ""
    crm_api_key: str = ""

    @property
    def crm_enabled(self) -> bool:
        """Мост в CRM включён: заданы и адрес приёма, и ключ."""
        return bool(self.crm_ingest_url.strip() and self.crm_api_key.strip())

    @property
    def admin_id_list(self) -> list[int]:
        """Список ID администраторов."""
        # Пустые и нечисловые значения молча отбрасываем
        result = []
        for raw in (self.admin_ids or "").split(","):
            raw = raw.strip()
            if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
                result.append(int(raw))
        return result

    # TON Payments
    ton_wallet_address: str = ""
    ton_api_key: str = ""
    ton_api_url: str = "https://toncenter.com/api/v2"
    # Сколько ждём поступления перевода TON
    ton_payment_timeout_seconds: int = 1800
    # Как часто опрашиваем блокчейн
    ton_poll_interval_seconds: int = 60

    # Монетизация: платит перевозчик за публикацию рейса.
    # Пока идёт пробный период, ответы на заявки открыты всем бесплатно.
    # Формат: YYYY-MM-DD. Пустая строка — пробного периода нет.
    free_access_until: str = ""


    # Дневной тариф перевозчика в звёздах. Списывается один раз в сутки,
    # в день первого ответа на заявку. Отправитель не платит никогда.
    daily_fee_stars: int = 30

    # Сколько активных дней даётся бесплатно новому перевозчику.
    # Активный день — день, когда он реально отвечал на заявки.
    trial_active_days: int = 14

    # Пакеты пополнения баланса в звёздах. Произвольные суммы запрещены:
    # payload счёта формирует сервер, подменить сумму нельзя.
    topup_packages_stars: str = "50,100,250,500,1000"

    # Ориентировочная стоимость одной звезды в долларах — для пересчёта в TON
    star_usd_rate: float = 0.02

    @property
    def topup_packages(self) -> list[int]:
        """Разрешённые суммы пополнения."""
        result = []
        for raw in (self.topup_packages_stars or "").split(","):
            raw = raw.strip()
            if raw.isdigit() and int(raw) > 0:
                result.append(int(raw))
        return sorted(set(result))

    # Сколько закрытых доставок нужно перевозчику для автоматической галочки
    verified_deliveries_threshold: int = 5

    # Subscription prices (USD) — второй тариф для тех, кто летает часто
    subscription_monthly_price: float = 40.0
    subscription_quarterly_price: float = 100.0
    subscription_yearly_price: float = 300.0

    # Куда складываются загруженные фотографии посылок
    media_root: str = "/app/media"

    # Logging
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # .env общий с docker-compose и Vite (POSTGRES_PASSWORD, VITE_API_URL...):
        # чужие ключи не наши — молча пропускаем, а не падаем на старте
        "extra": "ignore",
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
