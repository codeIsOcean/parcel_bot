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


# Сигнатуры файлов: заголовку Content-Type от клиента не верим
_MAGIC = {
    ".jpg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
    ".heic": (b"ftyp",),
}

# Сколько файлов в сутки может загрузить один пользователь
MAX_UPLOADS_PER_DAY = 40

# Учёт загрузок за день: user_id → (день, сколько)
_uploads_today: dict[int, tuple[str, int]] = {}


def _looks_like(content: bytes, extension: str) -> bool:
    """Совпадает ли начало файла с сигнатурой заявленного типа."""
    head = content[:16]
    for magic in _MAGIC.get(extension, ()):
        # ftyp у HEIC стоит с 4-го байта, у остальных — с нулевого
        if head.startswith(magic) or (extension == ".heic" and head[4:8] == magic):
            return True
    return False


def check_upload_quota(user_id: int) -> None:
    """Дневная квота на загрузки — чтобы одним аккаунтом не забить диск."""
    today = date.today().isoformat()
    day, count = _uploads_today.get(user_id, (today, 0))
    if day != today:
        count = 0
    if count >= MAX_UPLOADS_PER_DAY:
        raise MediaError("upload_quota_exceeded")
    _uploads_today[user_id] = (today, count + 1)
    # Не даём словарю расти бесконечно
    if len(_uploads_today) > 10000:
        for key in [k for k, (d, _) in _uploads_today.items() if d != today]:
            _uploads_today.pop(key, None)


async def read_limited(file, limit: int = MAX_FILE_BYTES) -> bytes:
    """Прочитать загрузку кусками и оборвать, как только она превысила лимит."""
    chunks = []
    total = 0
    while True:
        chunk = await file.read(256 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise MediaError("file_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def save_bytes(content: bytes, content_type: str, subdir: str) -> str:
    """Сохранить файл и вернуть относительный путь."""
    extension = ALLOWED_TYPES.get((content_type or "").lower())
    if not extension:
        raise MediaError("unsupported_type")

    if not content:
        raise MediaError("empty_file")

    if len(content) > MAX_FILE_BYTES:
        raise MediaError("file_too_large")

    # Внутри должна быть картинка заявленного типа, а не что угодно с нужным заголовком
    if not _looks_like(content, extension):
        raise MediaError("unsupported_type")

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
