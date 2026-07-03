import json
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)

# Redis-клиент для хранения слотов (инициализируется при старте бота)
_redis = None

# Fallback — in-memory хранилище (если Redis недоступен)
_slots_fallback: dict[int, dict[str, int]] = {}

# Префикс ключей в Redis
_REDIS_PREFIX = "parcel_bot:screen:"


async def init_screen_storage(redis_url: str | None = None):
    """Инициализировать Redis-хранилище для ScreenManager."""
    global _redis
    if not redis_url:
        logger.warning("[SCREEN] Redis URL не указан, используется in-memory fallback")
        return

    try:
        from redis.asyncio import from_url
        _redis = from_url(redis_url, decode_responses=True)
        await _redis.ping()
        logger.info("[SCREEN] Redis-хранилище подключено")
    except Exception as e:
        logger.warning("[SCREEN] Не удалось подключиться к Redis: %s, используется fallback", e)
        _redis = None


async def _get_slots(chat_id: int) -> dict[str, int]:
    """Получить слоты пользователя из хранилища."""
    if _redis:
        try:
            data = await _redis.get(f"{_REDIS_PREFIX}{chat_id}")
            return json.loads(data) if data else {}
        except Exception:
            pass
    return _slots_fallback.get(chat_id, {})


async def _set_slots(chat_id: int, slots: dict[str, int]):
    """Сохранить слоты пользователя в хранилище."""
    if _redis:
        try:
            # TTL 24 часа — автоматическая очистка неактивных пользователей
            await _redis.set(f"{_REDIS_PREFIX}{chat_id}", json.dumps(slots), ex=86400)
            return
        except Exception:
            pass
    _slots_fallback[chat_id] = slots


async def _pop_slot(chat_id: int, slot: str) -> int | None:
    """Извлечь и удалить слот из хранилища."""
    slots = await _get_slots(chat_id)
    msg_id = slots.pop(slot, None)
    if msg_id is not None:
        await _set_slots(chat_id, slots)
    return msg_id


class ScreenManager:
    """
    Единая система отправки UI-сообщений в боте.
    Слоты: main (ReplyKeyboard), inline (InlineKeyboard), temp (временное).
    Автоматически удаляет предыдущее сообщение в слоте.
    Хранит состояние в Redis (с fallback на in-memory dict).
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def show(
        self,
        chat_id: int,
        text: str,
        slot: str = "main",
        reply_markup: Optional[InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove] = None,
        photo: Optional[str] = None,
        auto_delete_sec: Optional[int] = None,
    ) -> int | None:
        """
        Показать сообщение в слоте.
        Автоматически удаляет предыдущее сообщение в этом слоте.
        """
        # Удаляем предыдущее сообщение в слоте (кроме main с ReplyKeyboard)
        if slot in ("inline", "temp"):
            await self._delete_slot(chat_id, slot)

        try:
            # Отправляем сообщение
            if photo:
                msg = await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                )
            else:
                msg = await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                )

            # Сохраняем ID сообщения в слоте
            slots = await _get_slots(chat_id)
            slots[slot] = msg.message_id
            await _set_slots(chat_id, slots)

            logger.debug("[SCREEN] show: chat=%s, slot=%s, msg_id=%s", chat_id, slot, msg.message_id)
            return msg.message_id

        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            logger.warning("[SCREEN] Пользователь %s заблокировал бота", chat_id)
            return None
        except TelegramBadRequest as e:
            logger.error("[SCREEN] Ошибка отправки: chat=%s, error=%s", chat_id, e)
            return None

    async def edit(
        self,
        chat_id: int,
        text: str,
        slot: str = "inline",
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        """Редактировать сообщение в слоте (для inline callback)."""
        slots = await _get_slots(chat_id)
        msg_id = slots.get(slot)
        if not msg_id:
            # Нет сообщения для редактирования — отправляем новое
            await self.show(chat_id, text, slot=slot, reply_markup=reply_markup)
            return True

        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=reply_markup,
            )
            return True
        except TelegramBadRequest:
            # Сообщение не изменилось или удалено — отправляем новое
            await self.show(chat_id, text, slot=slot, reply_markup=reply_markup)
            return True

    async def delete_slot(self, chat_id: int, slot: str) -> bool:
        """Удалить сообщение в слоте (публичный метод)."""
        return await self._delete_slot(chat_id, slot)

    async def _delete_slot(self, chat_id: int, slot: str) -> bool:
        """Удалить сообщение в слоте."""
        msg_id = await _pop_slot(chat_id, slot)
        if not msg_id:
            return False

        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            return True
        except (TelegramBadRequest, TelegramForbiddenError):
            # Сообщение уже удалено или бот заблокирован — ОК
            return False

    async def clear_all(self, chat_id: int) -> None:
        """Удалить все сообщения пользователя из всех слотов."""
        slots = await _get_slots(chat_id)
        for slot, msg_id in slots.items():
            try:
                await self.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except (TelegramBadRequest, TelegramForbiddenError):
                pass
        # Очищаем все слоты
        await _set_slots(chat_id, {})
