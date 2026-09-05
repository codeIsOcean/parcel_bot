"""Мост чата поддержки во внешнюю CRM (KVD Ads Panel, вкладка «Посылки»).

Каждое сообщение переписки с поддержкой (пользователь ↔ администратор)
дублируется в панель cabinet.kazakhindubai.com, чтобы владелец видел обращения
из всех проектов на одном экране и отвечал оттуда. Ответ из панели приходит
обратно через backend/app/routers/internal_crm.py.

Принципы:
  • Единственная точка исходящей связи с CRM — этот модуль. Вызывает его
    только support_service после коммита в базу, а не роуты и не хендлеры.
  • Best-effort: CRM недоступна → пользователь и администратор ничего не
    замечают, сообщение уже сохранено у нас. Три попытки с паузой, потом лог.
  • Выключен, пока в .env нет CRM_INGEST_URL и CRM_API_KEY — тогда ни одного
    HTTP-запроса не делается (тесты, локалка, прод без панели).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Паузы между попытками (сек): растущая задержка
RETRY_DELAYS = (1.0, 3.0, 9.0)

# Таймаут одного запроса к CRM (сек)
REQUEST_TIMEOUT = 10.0

# Кто написал: пользователь Mini App или администратор (из бота)
SENDER_USER = "user"
SENDER_OPERATOR = "operator"


@dataclass
class CrmEvent:
    """Одно сообщение чата поддержки для отправки в CRM."""

    # Кто написал: user / operator
    sender: str
    # Telegram ID пользователя — ключ диалога в CRM
    user_id: int
    # Текст сообщения
    text: str
    # ID сообщения в нашей базе — идемпотентность на стороне CRM
    external_id: int
    # ID обращения в нашей базе
    session_id: int
    # Когда написано
    created_at: datetime | None
    # Снимок карточки клиента (имя, телефон, роль, город, рейтинг)
    client: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """JSON-тело запроса в CRM."""
        return {
            "event": "message",
            "sender": self.sender,
            "user_id": self.user_id,
            "text": self.text,
            "external_id": str(self.external_id),
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "client": self.client,
        }


class CrmBridge:
    """Исходящая связь поддержки с внешней CRM."""

    def __init__(self) -> None:
        # Живые фоновые задачи держим, чтобы сборщик мусора их не убил
        self._tasks: set[asyncio.Task] = set()

    @property
    def enabled(self) -> bool:
        """Мост включён, только если заданы и адрес, и ключ."""
        return settings.crm_enabled

    def schedule(self, event: CrmEvent) -> asyncio.Task | None:
        """Поставить событие в фоновую отправку. None — мост выключен.

        Вызывать после коммита в базу: иначе в CRM может уехать сообщение,
        которого у нас в итоге нет.
        """
        if not self.enabled:
            return None
        task = asyncio.create_task(self.send(event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def send(self, event: CrmEvent) -> bool:
        """Отправить событие с ретраями. True — CRM приняла (2xx)."""
        headers = {"X-API-Key": settings.crm_api_key.strip()}
        payload = event.to_payload()
        url = settings.crm_ingest_url.strip()

        for attempt, delay in enumerate(RETRY_DELAYS, start=1):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                if 200 <= resp.status_code < 300:
                    return True
                # Ошибка в данных или ключе — повторять бессмысленно
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    logger.warning(
                        "[CRM_BRIDGE] rejected: user=%s status=%s body=%s",
                        event.user_id, resp.status_code, resp.text[:200],
                    )
                    return False
                logger.warning("[CRM_BRIDGE] attempt %s failed: status=%s", attempt, resp.status_code)
            except Exception as e:  # noqa: BLE001 — сеть, таймаут, DNS
                logger.warning("[CRM_BRIDGE] attempt %s error: %s", attempt, e)
            if attempt < len(RETRY_DELAYS):
                await asyncio.sleep(delay)

        # Сообщение у нас сохранено, CRM догонит при следующем
        logger.error("[CRM_BRIDGE] giving up: user=%s external_id=%s", event.user_id, event.external_id)
        return False


# Единственный экземпляр моста
crm_bridge = CrmBridge()
