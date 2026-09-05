# Чат поддержки ↔ KVD Ads Panel (CRM)

**Parcel Bot, 2026-09-06.** Сообщения чата поддержки (пользователь ↔ администратор)
из Mini App дублируются в KVD-панель (`cabinet.kazakhindubai.com/crm`, вкладка
«📦 Посылки»), ответ оператора из панели приходит пользователю от нашего бота.
Поведение приложения и бота не менялось: администратор по-прежнему может
отвечать из Telegram (кнопка «Ответить», `/support_queue`), а теперь и из панели.
Сделано по образцу такси-ботов (ZuZu / Дубай), см. их `docs/CRM_BRIDGE.md`.

## Единые системы
| Задача | Где |
|---|---|
| Сценарий поддержки (сообщение юзера, ответ админа, пуши, зеркало в CRM) | `backend/app/services/support_service.py` |
| Исходящий мост в CRM (best-effort, ретраи, выключен без настроек) | `backend/app/services/crm_bridge.py` |
| Приём ответа из CRM (X-API-Key) | `backend/app/routers/internal_crm.py` — `POST /api/v1/internal/crm/reply` |
| Ответ администратора из Telegram | `bot/handlers/support_admin.py` → `support_service.send_admin_reply(origin="app")` |

Сообщение сначала ложится в базу (коммит), потом уходят пуши и копия в CRM.
Ответ с `origin="crm"` в CRM не возвращается (нет петли). Бот-контейнер
запускает тот же `support_service`, поэтому ответы из Telegram тоже
зеркалятся в панель — `.env` у бота и бэкенда общий.

## Что уходит в CRM
JSON: `sender` (user/operator), `user_id`, `text`, `external_id` (id сообщения у нас —
идемпотентность), `session_id`, `created_at`, `client` (снимок карточки: имя, username,
телефон, город, язык, роль sender/traveler/both, регистрация, `details` — рейтинг,
доставки, проверен, премиум, баланс ⭐, блокировка). Медиа в чате поддержки нет.

## Доступность поддержки
`support_service.is_available()` — есть администраторы в Telegram **или** включён
мост в CRM. Без того и другого Mini App показывает «поддержка недоступна» (503).

## Настройка (.env)
```
CRM_INGEST_URL=https://cabinet.kazakhindubai.com/api/v1/crm/ingest
CRM_API_KEY=<общий секрет источника>   # тот же в .env.prod кабинета как CRM_PARCEL_API_KEY
```
Оба пустые → мост выключен, роут ответа отвечает 404.
Секрет: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Тесты
`tests/test_crm_bridge.py`, `tests/test_support_chat.py` (зеркало в CRM, ответ из CRM),
`tests/test_internal_crm_route.py`.
Панель: `test_kvdModerBotProd/docs/aika_supportchat/EXTERNAL_SOURCES.md`.
