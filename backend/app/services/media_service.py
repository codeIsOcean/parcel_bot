"""Хранение фотографий посылок.

Mini App не может получить идентификатор файла Telegram, поэтому снимки
приходят обычной загрузкой на бэкенд и складываются в том на диске.
В базе хранится относительный путь, наружу отдаётся адрес под /media.

Проверяем три вещи: тип содержимого, размер и расширение. Имя файла всегда
генерируем сами — пользовательское имя в путь не попадает.
"""

import logging
import secrets
from datetime import date
from pathlib import Path

from backend.app.config import settings

logger = logging.getLogger(__name__)

# Разрешённые типы и соответствующие расширения
ALLOWED_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}

# Максимальный размер одного файла
MAX_FILE_BYTES = 8 * 1024 * 1024

# Сколько снимков разрешаем на один этап
MAX_FILES_PER_STEP = 5


class MediaError(Exception):
    """Файл не принят."""


def media_root() -> Path:
    """Каталог, куда складываются файлы."""
    root = Path(settings.media_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def public_url(relative_path: str) -> str:
    """Адрес файла для фронта."""
    return f"/media/{relative_path.lstrip('/')}"


def save_bytes(content: bytes, content_type: str, subdir: str) -> str:
    """Сохранить файл и вернуть относительный путь."""
    extension = ALLOWED_TYPES.get((content_type or "").lower())
    if not extension:
        raise MediaError("unsupported_type")

    if not content:
        raise MediaError("empty_file")

    if len(content) > MAX_FILE_BYTES:
        raise MediaError("file_too_large")

    # Раскладываем по датам, чтобы каталог не разрастался в одну кучу
    day = date.today().isoformat()
    relative_dir = f"{subdir}/{day}"
    target_dir = media_root() / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    # Имя генерируем сами: пользовательское в путь не попадает
    name = f"{secrets.token_hex(12)}{extension}"
    (target_dir / name).write_bytes(content)

    relative_path = f"{relative_dir}/{name}"
    logger.info("[MEDIA] Сохранён файл %s (%s байт)", relative_path, len(content))
    return relative_path


def merge_paths(existing: str | None, new_paths: list[str]) -> str:
    """Дописать пути к уже сохранённым, соблюдая лимит на этап."""
    current = [p for p in (existing or "").split(",") if p.strip()]
    combined = current + new_paths
    # Лишние снимки просто отбрасываем, ошибку не поднимаем
    return ",".join(combined[:MAX_FILES_PER_STEP])


def to_urls(stored: str | None) -> list[str]:
    """Разобрать хранимое поле в список адресов для фронта."""
    if not stored:
        return []
    return [public_url(p.strip()) for p in stored.split(",") if p.strip()]
