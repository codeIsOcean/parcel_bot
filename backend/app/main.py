import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from backend.app.routers import (
    auth, parcels, flights, users, chats, matches, subscriptions, cities, reports,
    wallet, support, media, internal_crm, admin,
)
from backend.app.services.access_service import PaymentRequiredError
from backend.app.services.moderation_service import ProhibitedContentError

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

async def _ton_poller():
    """Фоновый опрос блокчейна: ищем поступившие переводы TON.

    Нужен потому, что TON не умеет уведомлять нас сам. Цикл переживает любые
    ошибки: сбой одного прохода не должен гасить задачу целиком.
    """
    from backend.app.database import async_session
    from backend.app.services import payment_service

    while True:
        try:
            await asyncio.sleep(settings.ton_poll_interval_seconds)
            async with async_session() as session:
                credited = await payment_service.check_ton_payments(session)
                if credited:
                    logger.info("[TON] Зачислено платежей: %s", credited)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("[TON] Ошибка цикла опроса: %s", e)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Lifecycle — запуск и остановка приложения."""
    logger.info("[API] Parcel Bot API запущен на %s:%s", settings.api_host, settings.api_port)

    # Опрос TON запускаем только если кошелёк настроен
    poller = None
    if settings.ton_wallet_address:
        poller = asyncio.create_task(_ton_poller())
        logger.info("[TON] Опрос поступлений запущен")

    yield

    if poller:
        poller.cancel()

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


@app.exception_handler(ProhibitedContentError)
async def prohibited_content_handler(request: Request, exc: ProhibitedContentError):
    """Ответ на попытку отправить запрещённое вложение."""
    return JSONResponse(
        status_code=422,
        content={"detail": "prohibited_content", "terms": exc.terms},
    )


@app.exception_handler(PaymentRequiredError)
async def payment_required_handler(request: Request, exc: PaymentRequiredError):
    """Ответ на попытку ответить на заявку без оплаченного дня."""
    # 402 — фронт по этому коду показывает экран оплаты, а не общую ошибку
    return JSONResponse(
        status_code=402,
        content={
            "detail": "daily_fee_required",
            "price_stars": exc.price_stars,
            "balance_stars": exc.balance_stars,
        },
    )

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
app.include_router(reports.router, prefix="/api/v1")
app.include_router(wallet.router, prefix="/api/v1")
app.include_router(support.router, prefix="/api/v1")
app.include_router(internal_crm.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


# Раздача загруженных фотографий
Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_root), name="media")


@app.get("/health")
async def health_check():
    """Health check для Docker / мониторинга."""
    return {"status": "ok"}
