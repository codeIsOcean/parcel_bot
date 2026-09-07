# Parcel Bot — CLAUDE.md

## Описание проекта
Сервис доставки посылок через попутчиков на международных рейсах.
Две роли: Отправитель и Перевозчик. Telegram Mini App + Telegram Bot.

## Стек технологий
- **Bot:** Python, aiogram 3, FSM (RedisStorage), ScreenManager
- **Backend:** Python, FastAPI, SQLAlchemy (async), Pydantic, JWT
- **WebApp:** Vue 3, Vite, Pinia, Vue Router, Axios, TailwindCSS
- **БД:** PostgreSQL (prod), SQLite (dev)
- **Кеш/FSM:** Redis
- **Платежи:** Telegram Stars, TON

## Структура проекта
```
parcel_bot/
├── bot/                # Telegram Bot (aiogram 3)
├── backend/            # FastAPI API
├── webapp/             # Vue 3 Mini App
├── shared/             # Общие модели, locale, утилиты
├── alembic/            # Миграции БД
├── docs/               # Документация
│   ├── CHECKLIST.md
│   ├── WEB_CHECKLIST.md
│   └── DEVELOPER_RULES.md
└── docker-compose.yml
```

## Архитектура: Mini App-first (решение владельца 2026-09-07)
Вся операционка — посылки, рейсы, отклики, чаты, оценки, профиль, оплата, админка — живёт
в **Mini App**. Бот — тонкая обёртка: вход и онбординг (язык → телефон), уведомления с кнопкой
на нужный экран, приём оплаты Stars, ответы поддержки, реестр групп. Операционных хендлеров
и reply-меню в боте НЕТ и добавлять их не нужно. Контракт: `docs/BOT_VS_MINIAPP.md`.
Админ-панель: `docs/ADMIN_PANEL.md`. Группы и кросс-постинг: `docs/GROUPS.md`.

## Критические правила
1. **DEVELOPER_RULES.md** — ОБЯЗАТЕЛЬНО читать перед работой
2. **CHECKLIST.md** — проверять ПОСЛЕ каждой задачи
3. Все тексты через locale (i18n), НЕ хардкод
4. ScreenManager для ВСЕХ сообщений бота
5. Тонкие handlers (<=25 строк), логика в services
6. Комментарии на русском над каждой значимой строкой
7. Edge cases обязательны (bot blocked, API error, empty data)

## Тестовый бот (Telegram)
- **Имя:** Посылка Бот Тест | Parcel Bot Test
- **Username:** @parcel07test_bot
- **Описание:** This is a test of Parcel Bot

## Продакшн-сервер
- **IP:** 80.209.231.69 (новый сервер), проект в `/opt/parcel_bot`, compose — `docker-compose.prod.yml`
- **Доступ:** `ssh root@80.209.231.69` (ключ ~/.ssh/id_ed25519)
- **Деплой:** push в main → CI: тесты + одна голова Alembic → сборка образов → на сервере
  дамп БД → `alembic upgrade head` (падение = красный деплой) → graceful `up -d`
- **Обязательные переменные `.env` на сервере:** `BOT_USERNAME` (кнопки в группах), `ADMIN_IDS`, `WEBAPP_URL`

### Контейнеры на сервере
| Контейнер | Описание | Порт |
|-----------|----------|------|
| `parcel_bot_api` | FastAPI backend | 8091→8000 |
| `parcel_bot_tg` | Telegram Bot (aiogram) | — |
| `parcel_bot_webapp` | Vue 3 Mini App | 8092→80 |
| `parcel_bot_db` | PostgreSQL 16 | 5432 (internal) |
| `parcel_bot_redis` | Redis 7 | 6379 (internal) |

### Команды проверки на сервере
```bash
# Подключение к серверу
ssh root@176.223.129.98

# Статус всех контейнеров parcel_bot
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep parcel

# Логи контейнера (последние 50 строк)
docker logs parcel_bot_api --tail=50
docker logs parcel_bot_tg --tail=50

# Перезапуск контейнера
docker restart parcel_bot_api
docker restart parcel_bot_tg

# Миграции вручную (из /opt/parcel_bot)
docker compose -f docker-compose.prod.yml run --rm --no-deps bot alembic upgrade head
```
⚠️ `docker compose down -v` ЗАПРЕЩЁН — тома БД внешние, но не рисковать.

## Команды разработки (локально)
```bash
# WebApp dev server
cd webapp && npm run dev

# Backend
cd backend && uvicorn app.main:app --reload

# Bot
cd bot && python main.py

# Alembic миграции
alembic upgrade head
alembic revision --autogenerate -m "description"
```
