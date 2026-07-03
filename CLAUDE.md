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

## Критические правила
1. **DEVELOPER_RULES.md** — ОБЯЗАТЕЛЬНО читать перед работой
2. **CHECKLIST.md** — проверять ПОСЛЕ каждой задачи
3. Все тексты через locale (i18n), НЕ хардкод
4. ScreenManager для ВСЕХ сообщений бота
5. Тонкие handlers (<=25 строк), логика в services
6. Комментарии на русском над каждой значимой строкой
7. Edge cases обязательны (bot blocked, API error, empty data)

## Команды разработки
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
