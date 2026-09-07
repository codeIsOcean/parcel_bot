# Безопасность — аудит 2026-09-07 и что сделано

## Сделано в коде (этот же день)
| Риск | Фикс |
|---|---|
| Секреты в публичном репо (`.env.test`) | файл снят с отслеживания, `.env.*` в `.gitignore`. **Секреты считать скомпрометированными — см. «Действия владельца»** |
| Любой мог заблокировать любого тремя жалобами | жалоба только по своей сделке (оба — участники посылки); автоблок по ≥3 **разным** авторам; админов не блокирует |
| HTML-инъекция в уведомления (parse_mode=HTML) | `nt()` экранирует все подстановки; двойное экранирование убрано |
| Перебор кода выдачи (4 цифры, без лимита) | 6 цифр, `hmac.compare_digest`, 5 попыток → `handover_locked` (миграция 007) |
| Rate limiting видел всех как один IP | uvicorn `--proxy-headers --forwarded-allow-ips='*'` (порт только на localhost за nginx) |
| Чат и пуши любому по `traveler_id` в теле запроса | `traveler_id` от клиента игнорируется, перевозчик только через принятую заявку |
| Подписка без проверки оплаты | `POST /subscriptions` → 501 до реализации; карточка скрыта |
| Публичные профили/рейсы без авторизации (перебор PII) | `GET /users/{id}`, `/users/{id}/reviews`, `/flights/{id}` только с токеном |
| Медиа: доверие Content-Type, чтение в память, без квот | сигнатуры файлов, чтение с потолком 8 МБ, квота 40/сутки |
| Дефолтный `SECRET_KEY` только предупреждал | `RuntimeError` при дефолтном/пустом ключе; initData без `BOT_TOKEN` не принимаются; `auth_date` обязателен |
| Webhook без секрета = поддельные платежи | старт с `USE_WEBHOOK` без `WEBHOOK_SECRET` запрещён |
| Уязвимые зависимости | `python-jose` → `PyJWT 2.9`, `python-multipart 0.0.18`, `aiohttp 3.10.11` |
| `/docs`, `/redoc`, `/openapi.json` наружу | выключены (флаг `EXPOSE_DOCS=true` для стенда); из nginx убраны |
| Нет security-заголовков, `/media/` не проксировался | HSTS, nosniff, Referrer-Policy, `frame-ancestors` только Telegram; `location /media/` |
| Гонка при двойном «принять» | `SELECT … FOR UPDATE` на посылке; валидация рейса и веса в заявке |
| Refresh-токен 7 дней без отзыва | сокращён до 2 дней (ротация с `jti` — в планах) |
| Ручная проверка TON била в toncenter без ограничений | кэш ответа 15 с |
| dev-compose открывал Postgres/Redis на 0.0.0.0 | только `127.0.0.1` |

## Действия владельца (нельзя сделать из кода)
1. **BotFather → `/revoke`** токен @parcel07test_bot, новый токен — в `.env` сервера (`BOT_TOKEN`).
2. **Новый `SECRET_KEY`** (`python3 -c "import secrets; print(secrets.token_hex(32))"`) в `.env` сервера — все сессии разлогинятся, это нормально.
3. **Новый пароль Postgres** на сервере (`ALTER USER postgres PASSWORD '…'`) + `POSTGRES_PASSWORD`/`DATABASE_URL` в `.env`, перезапуск api и бота.
4. Опционально: вычистить `.env.test` из истории git (`git filter-repo`) и включить GitHub Secret Scanning. Утечку это не отменяет, но убирает ключи из выдачи.
5. В GitHub → Settings → Code security включить Push protection.

## Что осталось в планах
- Ротация refresh-токенов (`jti` + Redis denylist), лимиты на сообщения чата по `user.id`.
- Хранилище rate limiting в Redis (сейчас in-memory, один воркер).
