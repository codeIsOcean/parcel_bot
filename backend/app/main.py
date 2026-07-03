import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from backend.app.routers import auth, parcels, flights, users, chats, matches, subscriptions, cities

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Lifecycle — запуск и остановка приложения."""
    logger.info("[API] Parcel Bot API запущен на %s:%s", settings.api_host, settings.api_port)
    yield
    logger.info("[API] Parcel Bot API остановлен")


# Создаём FastAPI приложение
# Rate limiter — защита от брутфорса
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Parcel Bot API",
    description="API для сервиса доставки посылок через попутчиков",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Подключаем rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — разрешаем запросы от Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin for origin in [
            "https://web.telegram.org",
            "https://telegram.org",
            "https://fly.kazakhindubai.com",
            settings.webapp_url,
            "http://localhost:3000",  # Dev
        ] if origin  # Фильтруем пустые строки
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router, prefix="/api/v1")
app.include_router(parcels.router, prefix="/api/v1")
app.include_router(flights.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(cities.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check для Docker / мониторинга."""
    return {"status": "ok"}
