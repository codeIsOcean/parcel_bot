"""Единый канал отправки сообщений в Telegram.

Нужен бэкенду: пользователь совершает действие в Mini App, а уведомление
должно прилететь второй стороне в чат с ботом. Бот и бэкенд — разные
процессы, поэтому бэкенд ходит в Bot API напрямую по HTTP тем же токеном.

Все вызовы безопасны: ни одна ошибка отправки не должна ронять запрос,
из которого уведомление было инициировано.
"""

import asyncio
import logging

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Базовый адрес Bot API
_API_URL = "https://api.telegram.org/bot{token}/{method}"

# Держим ссылки на фоновые задачи, иначе сборщик мусора может их убить
_background_tasks: set[asyncio.Task] = set()

# Сколько раз повторяем при сетевой ошибке или 5xx
_MAX_RETRIES = 2

# Таймаут одного запроса к Bot API
_TIMEOUT = 10.0


class TelegramSendResult:
    """Итог отправки: доставлено ли и заблокирован ли бот пользователем."""

    __slots__ = ("ok", "blocked")

    def __init__(self, ok: bool, blocked: bool = False):
        self.ok = ok
        self.blocked = blocked


async def _call_api(method: str, payload: dict) -> TelegramSendResult:
    """Вызвать метод Bot API с ретраями. Исключения наружу не пробрасываем."""
    # Без токена отправлять некуда — молча выходим, чтобы не спамить логи в тестах
    if not settings.bot_token:
        logger.warning("[NOTIFY] BOT_TOKEN не задан, отправка пропущена: %s", method)
        return TelegramSendResult(False)

    url = _API_URL.format(token=settings.bot_token, method=method)

    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(url, json=payload)

            # Успех
            if response.status_code == 200:
                return TelegramSendResult(True)

            # Пользователь заблокировал бота или удалил чат — повторять бессмысленно
            if response.status_code == 403:
                logger.info("[NOTIFY] Бот заблокирован: chat_id=%s", payload.get("chat_id"))
                return TelegramSendResult(False, blocked=True)

            # Флуд-контроль — ждём столько, сколько просит Telegram
            if response.status_code == 429:
                retry_after = 1.0
                try:
                    retry_after = float(response.json()["parameters"]["retry_after"])
                except Exception:
                    pass
                logger.warning("[NOTIFY] Флуд-контроль, ждём %.1fs", retry_after)
                await asyncio.sleep(min(retry_after, 30.0))
                continue

            # Ошибка на стороне Telegram — можно повторить
            if response.status_code >= 500:
                logger.warning("[NOTIFY] Telegram %s, попытка %s", response.status_code, attempt + 1)
                await asyncio.sleep(1.0 * (attempt + 1))
                continue

            # Остальные 4xx — наша ошибка в запросе, повторять нет смысла
            logger.error(
                "[NOTIFY] Ошибка %s для chat_id=%s: %s",
                response.status_code, payload.get("chat_id"), response.text[:300],
            )
            return TelegramSendResult(False)

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning("[NOTIFY] Сеть недоступна (%s), попытка %s", type(e).__name__, attempt + 1)
            await asyncio.sleep(1.0 * (attempt + 1))
        except Exception as e:
            # Ловим всё: уведомление никогда не должно ломать вызывающий код
            logger.exception("[NOTIFY] Непредвиденная ошибка отправки: %s", e)
            return TelegramSendResult(False)

    logger.error("[NOTIFY] Не удалось отправить после %s попыток: chat_id=%s",
                 _MAX_RETRIES + 1, payload.get("chat_id"))
    return TelegramSendResult(False)


async def call_api(method: str, payload: dict) -> dict | None:
    """Вызвать произвольный метод Bot API и вернуть поле result.

    Нужен сервисам, которым мало отправки сообщения: например, создание
    ссылки на счёт для Mini App через createInvoiceLink.
    """
    if not settings.bot_token:
        logger.warning("[NOTIFY] BOT_TOKEN не задан, вызов %s пропущен", method)
        return None

    url = _API_URL.format(token=settings.bot_token, method=method)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
        data = response.json()
    except Exception as e:
        logger.exception("[NOTIFY] Ошибка вызова %s: %s", method, e)
        return None

    # Telegram всегда отвечает полем ok
    if not data.get("ok"):
        logger.error("[NOTIFY] %s вернул ошибку: %s", method, str(data)[:300])
        return None

    return data.get("result")


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
    disable_notification: bool = False,
) -> TelegramSendResult:
    """Отправить сообщение пользователю в Telegram."""
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": disable_notification,
        "link_preview_options": {"is_disabled": True},
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    return await _call_api("sendMessage", payload)


async def send_message_id(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> int | None:
    """Отправить сообщение и вернуть его message_id (нужно постам в группах)."""
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    result = await call_api("sendMessage", payload)
    if not result:
        return None
    return result.get("message_id")


async def edit_message_text(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> bool:
    """Отредактировать текст сообщения. Пустой reply_markup снимает кнопки."""
    payload: dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
        # Явно пустая клавиатура убирает кнопку под закрытым объявлением
        "reply_markup": reply_markup or {"inline_keyboard": []},
    }
    return (await call_api("editMessageText", payload)) is not None


def webapp_button(text: str, path: str = "/") -> dict | None:
    """Инлайн-клавиатура с одной кнопкой, открывающей Mini App на нужном экране."""
    # Без публичного адреса Mini App кнопку построить нельзя
    base = (settings.webapp_url or "").rstrip("/")
    if not base.startswith("https://"):
        return None

    return {
        "inline_keyboard": [[
            {"text": text, "web_app": {"url": f"{base}{path}"}},
        ]]
    }


def fire_and_forget(coro) -> None:
    """Запустить корутину уведомления в фоне, не задерживая ответ API."""
    try:
        task = asyncio.create_task(coro)
    except RuntimeError:
        # Нет активного event loop (например, синхронный тест) — просто закрываем корутину
        coro.close()
        return

    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
