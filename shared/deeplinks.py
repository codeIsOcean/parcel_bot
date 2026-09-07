"""Диплинки в Mini App — единый словарь для бота, бэкенда и групп.

Один параметр запуска описывает экран приложения тремя способами:
- `https://t.me/<bot>?startapp=parcel_12` — прямое открытие Mini App
  (кнопки в группах: там web_app-кнопки запрещены);
- `/start parcel_12` — через личку бота (запасной путь, если Main App
  в BotFather не настроен или человеку сначала нужна регистрация);
- `?screen=parcel_12` в URL приложения — кнопка web_app из уведомления.

Mini App разбирает параметр одним и тем же `screen_path()`, поэтому
все три пути приводят на один экран.
"""

import re

# Допустимые параметры: сущность с числовым id или один из именованных экранов
_ENTITY_RE = re.compile(r"^(parcel|flight|profile|chat)_(\d{1,18})$")
_NAMED_SCREENS = {
    "publish": "/publish-flight",
    "send": "/send",
    "requests": "/requests",
    "parcels": "/parcels",
    "chats": "/chats",
    "wallet": "/wallet",
    "support": "/support",
    "admin": "/admin",
    "admin_support": "/admin?tab=support",
    "admin_groups": "/admin?tab=groups",
}

# Куда ведёт сущность внутри приложения
_ENTITY_PATHS = {
    "parcel": "/parcels/{id}",
    "flight": "/flights/{id}",
    "profile": "/profile/{id}",
    "chat": "/chats/{id}",
}


def parcel_param(parcel_id: int) -> str:
    """Параметр запуска для посылки."""
    return f"parcel_{parcel_id}"


def flight_param(flight_id: int) -> str:
    """Параметр запуска для рейса."""
    return f"flight_{flight_id}"


def is_valid_param(param: str | None) -> bool:
    """Понимаем ли мы такой параметр запуска."""
    if not param:
        return False
    return param in _NAMED_SCREENS or bool(_ENTITY_RE.match(param))


def screen_path(param: str | None) -> str:
    """Путь внутри Mini App для параметра запуска. Неизвестное — на главную."""
    if not param:
        return "/"
    if param in _NAMED_SCREENS:
        return _NAMED_SCREENS[param]
    match = _ENTITY_RE.match(param)
    if match:
        kind, entity_id = match.group(1), int(match.group(2))
        return _ENTITY_PATHS[kind].format(id=entity_id)
    return "/"


def startapp_url(bot_username: str, param: str | None = None) -> str | None:
    """Ссылка, открывающая Mini App напрямую (годится для кнопок в группах)."""
    # Без юзернейма бота ссылку не построить
    if not bot_username:
        return None
    base = f"https://t.me/{bot_username.lstrip('@')}"
    return f"{base}?startapp={param}" if param else base


def start_url(bot_username: str, param: str | None = None) -> str | None:
    """Ссылка в личку бота с payload — запасной путь через онбординг."""
    if not bot_username:
        return None
    base = f"https://t.me/{bot_username.lstrip('@')}"
    return f"{base}?start={param}" if param else base


def webapp_url(webapp_base: str, param: str | None = None) -> str | None:
    """Адрес Mini App с экраном в query — для web_app-кнопок в личке."""
    base = (webapp_base or "").rstrip("/")
    # Telegram принимает в web_app только https
    if not base.startswith("https://"):
        return None
    path = screen_path(param)
    return f"{base}{path}"
