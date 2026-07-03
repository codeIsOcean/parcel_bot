# Чек-лист проверки завершённых задач — Parcel Bot

> **Использование:** После завершения КАЖДОЙ задачи — пройти по этому чек-листу.
> Это предотвращает типичные ошибки из опыта модер-бота, такси-бота и goods tracker.

---

## 1. UX/UI проверки

### 1.1 Dead-End UX — КРИТИЧНО!

Каждая кнопка должна иметь обработчик. Нажатие без реакции = баг.

- [ ] Все `callback_data` проверены через grep
- [ ] Каждый callback имеет handler
- [ ] Нет "мёртвых" кнопок
- [ ] При ошибке — показать что делать дальше

**Проверка:**
```bash
# 1. Найти ВСЕ callback_data в клавиатурах
grep -rn "callback_data=" bot/keyboards/ | grep -oP "callback_data=['\"]([^'\"]+)" | sort -u > /tmp/callbacks.txt

# 2. Найти ВСЕ callback handlers
grep -rn "F\.data\." bot/handlers/ | sort -u > /tmp/handlers.txt

# 3. Сравнить — каждый callback_data ДОЛЖЕН иметь handler
```

### 1.2 Кнопка "Назад"

- [ ] Каждый экран имеет кнопку "Назад" или "Отмена"
- [ ] "Назад" возвращает на **предыдущий** экран (не в главное меню)
- [ ] "Назад" из FSM очищает текущий шаг, НЕ весь прогресс
- [ ] "Назад" на первом шаге FSM — возврат в меню

### 1.3 FSM и состояния

- [ ] Каждый FSM flow имеет кнопку "Отмена" на каждом шаге
- [ ] При завершении FSM — `await state.clear()`
- [ ] При ошибке в FSM — очистка state + возврат в меню
- [ ] Контекст навигации сохранён в state (`section`, `step`, `bot_message_id`)
- [ ] Timeout обработан — при бездействии N минут → автоочистка + уведомление

### 1.4 State Leak — КРИТИЧНО!

State Leak — когда пользователь застревает в FSM состоянии и бот перестаёт реагировать на команды.

- [ ] Catch-all handler НЕ перехватывает FSM сообщения
- [ ] FSM state очищается при ANY ошибке
- [ ] `/start` и `/menu` работают из ЛЮБОГО состояния (очищают FSM)
- [ ] Проверить: начать FSM → нажать /start → бот должен показать меню

```python
# ❌ НЕПРАВИЛЬНО — catch-all перехватывает FSM
@router.message()  # Перехватит ВСЁ, включая FSM ввод
async def catch_all(message: Message):
    await message.answer("Неизвестная команда")

# ✅ ПРАВИЛЬНО — catch-all с проверкой state
@router.message(StateFilter(None))  # Только если НЕТ активного FSM
async def catch_all(message: Message):
    await message.answer("Неизвестная команда. /menu — главное меню")
```

### 1.5 Message Clutter — накопление сообщений

- [ ] ScreenManager используется для всех сообщений (не `message.answer()`)
- [ ] Старые сообщения удаляются при переходе на новый экран
- [ ] `edit_text` используется для inline callback ответов (не `answer`)
- [ ] Временные сообщения (slot="temp") удаляются автоматически

### 1.6 Keyboard Flicker

- [ ] ReplyKeyboard НЕ пересоздаётся на каждое сообщение
- [ ] ReplyKeyboard обновляется ТОЛЬКО при смене экрана/роли
- [ ] На мобильных клавиатура НЕ мерцает при нажатии кнопок

### 1.7 Пагинация

- [ ] Списки > 10 элементов — пагинация (кнопки ◀️ ▶️)
- [ ] Показан номер страницы и общее количество
- [ ] Пустая страница — "Нет данных" (не пустой экран)

### 1.8 Пустые состояния

- [ ] Пустой список попутчиков → "Нет попутчиков. Попробуйте другой маршрут"
- [ ] Пустой список посылок → "У вас нет посылок. Создать?"
- [ ] Пустой список чатов → "Нет активных чатов"
- [ ] Пустой список рейсов → "Нет опубликованных рейсов. Создать?"
- [ ] Нет отзывов → "Пока нет отзывов"

---

## 2. Код и синтаксис

### 2.1 Python компиляция

- [ ] `python -m py_compile <file>` для каждого изменённого файла
- [ ] Нет SyntaxError, IndentationError

### 2.2 Импорты

- [ ] Нет unused imports
- [ ] Нет circular imports: `python -c "from bot.handlers import main_router"`
- [ ] Все новые файлы добавлены в `__init__.py` или router
- [ ] Новые роутеры включены в `main_router`

### 2.3 Роутеры и хендлеры

- [ ] Новый router зарегистрирован в `main_router.include_router()`
- [ ] Фильтры хендлеров НЕ конфликтуют (aiogram 3 — first match wins)
- [ ] Callback handler с `F.data.startswith("prefix:")` — не пересекается с другими
- [ ] FSM StateFilter используется правильно

### 2.4 Конфликты хендлеров

```python
# ❌ ОПАСНО — оба матчат "parcel:view:123"
@router.callback_query(F.data.startswith("parcel:"))
@router.callback_query(F.data.startswith("parcel:view:"))

# ✅ ПРАВИЛЬНО — конкретный фильтр первый, общий последний
@router.callback_query(F.data.startswith("parcel:view:"))  # Конкретный — первый
@router.callback_query(F.data.startswith("parcel:"))        # Общий — последний (fallback)
```

### 2.5 Аргументы функций

- [ ] Проверить сигнатуры перед вызовом
- [ ] НЕ передавать объект вместо int (user vs user.id)
- [ ] НЕ передавать str вместо int для ID

### 2.6 Перезапуск бота

- [ ] После изменений — перезапустить бота локально
- [ ] Проверить логи — нет ошибок при старте
- [ ] Проверить что хендлеры регистрируются

---

## 3. База данных

### 3.1 Alembic миграции

- [ ] `alembic heads` — ОДИН head (нет fork)
- [ ] `down_revision` указывает на РЕАЛЬНЫЙ предыдущий revision
- [ ] Revision ID уникальный и <= 32 символа
- [ ] `downgrade()` реализован (откат возможен)
- [ ] ENUM создаётся с `checkfirst=True`
- [ ] Проверка на чистой БД: `alembic upgrade head`

### 3.2 Silent Rollback — КРИТИЧНО!

```python
# ❌ КРИТИЧЕСКАЯ ОШИБКА — забыт commit()
async def create_parcel(session, data):
    parcel = Parcel(**data)
    session.add(parcel)
    # commit() забыт! Данные НЕ сохранятся, но ошибки НЕ будет!
    return parcel

# ✅ ПРАВИЛЬНО
async def create_parcel(session, data):
    parcel = Parcel(**data)
    session.add(parcel)
    await session.commit()  # ОБЯЗАТЕЛЬНО!
    await session.refresh(parcel)  # Получить сгенерированные поля (id, created_at)
    return parcel
```

- [ ] Каждый `session.add()` имеет `await session.commit()`
- [ ] После commit — `await session.refresh(obj)` если нужны auto-generated поля
- [ ] При ошибке — `await session.rollback()`

### 3.3 Модели SQLAlchemy

- [ ] Связи (ForeignKey) настроены правильно
- [ ] CASCADE/SET NULL для ondelete
- [ ] Индексы на часто запрашиваемые поля (user_id, status, from_city, to_city)
- [ ] ENUM типы соответствуют бизнес-логике

---

## 4. Безопасность и Edge Cases

- [ ] `TelegramForbiddenError` обработан (пользователь заблокировал бота)
- [ ] `TelegramBadRequest` обработан (сообщение удалено, чат не найден)
- [ ] `TelegramRetryAfter` обработан (rate limit — ждать и повторить)
- [ ] Все ID валидируются (int, положительные)
- [ ] Пользовательский ввод экранируется (`html.escape()`)
- [ ] Нет SQL injection (только ORM)
- [ ] `.env` НЕ в git (`check .gitignore`)

---

## 5. Telegram лимиты

- [ ] `callback_data` <= 64 байта (проверить длинные callback с ID)
- [ ] Текст сообщения <= 4096 символов (обрезать/пагинировать)
- [ ] Caption <= 1024 символа
- [ ] Текст кнопки <= 64 символа
- [ ] Количество кнопок в строке <= 8
- [ ] Размер фото <= 10 MB

---

## 6. Логирование

- [ ] Каждый handler/service логирует вход и результат
- [ ] Используются правильные уровни: `debug` / `info` / `warning` / `error`
- [ ] Формат: `[MODULE] описание: param1=%s, param2=%s`
- [ ] Ошибки логируются с `exc_info=True`
- [ ] Нет `print()` — только `logger`

```python
# ✅ ПРАВИЛЬНО
logger.info("[PARCEL] Создание посылки: user=%s, route=%s→%s", user_id, from_city, to_city)
# ... логика ...
logger.info("[PARCEL] Посылка создана: parcel_id=%s", parcel.id)

# При ошибке
logger.error("[PARCEL] Ошибка создания: user=%s, error=%s", user_id, e, exc_info=True)
```

---

## 7. Redis и состояния

- [ ] Ключи Redis с уникальными префиксами: `parcel_bot:fsm:`, `parcel_bot:cache:`
- [ ] TTL установлен для временных данных
- [ ] FSM storage = RedisStorage (не MemoryStorage в production)
- [ ] При перезапуске Redis — бот НЕ крашится (graceful fallback)

---

## 8. Хардкод — КРИТИЧНО!

- [ ] Тексты пользователю — через locale (`t(lang, "key")`), НЕ хардкод
- [ ] Города — из БД, НЕ из массива в коде
- [ ] Цены подписки — из конфига, НЕ из кода
- [ ] Лимиты (макс вес, кол-во фото) — из конфига
- [ ] URL, токены, ключи — из `.env`

---

## 9. Единые системы

- [ ] ScreenManager используется для ВСЕХ сообщений бота
- [ ] Locale используется для ВСЕХ текстов пользователю
- [ ] API Client (Vue) — единый axios instance с interceptors
- [ ] Pinia store — единый state management
- [ ] AuthService — единая авторизация (bot + webapp)
- [ ] Config — все настройки из одного места

---

## 10. Relay-чат

- [ ] Сообщения проходят через RelayService, НЕ напрямую
- [ ] Контакты скрыты до подтверждения обеими сторонами
- [ ] При блокировке бота получателем — уведомить отправителя
- [ ] Логирование: `[RELAY] from=%s to=%s parcel=%s`
- [ ] Чат деактивируется при завершении/отмене доставки

---

## 11. Подписки и платежи

- [ ] Подписка НЕ активируется без подтверждения оплаты
- [ ] Stars: `pre_checkout_query` → `successful_payment` → активация
- [ ] TON: проверка транзакции через TON API
- [ ] Логирование: `[PAYMENT] user=%s amount=%s method=%s status=%s`
- [ ] При истечении подписки — ограничение функций, НЕ удаление данных
- [ ] Напоминание за 3 дня до окончания

---

## 12. FSM диалоги — детальная проверка

### Создание посылки (7 шагов):
- [ ] Шаг 0: Город отправления — кнопки городов + "Другой город"
- [ ] Шаг 1: Город доставки — фильтр (не показывать тот же город)
- [ ] Шаг 2: Описание — текстовый ввод + валидация длины
- [ ] Шаг 3: Вес — кнопки (1, 2, 3, 5, 10 кг) + "Другой"
- [ ] Шаг 4: Фото — загрузка + "Пропустить"
- [ ] Шаг 5: Цена — кнопки + InDriver-style (+/-)
- [ ] Шаг 6: Подтверждение — показ всех данных + Подтвердить/Изменить/Отмена
- [ ] Каждый шаг: кнопка "Назад"
- [ ] "Другой город": свободный текстовый ввод → возврат в flow

### Публикация рейса (6 шагов):
- [ ] Шаг 0: Город отправления
- [ ] Шаг 1: Город прибытия
- [ ] Шаг 2: Дата вылета (валидация формата, не в прошлом)
- [ ] Шаг 3: Свободный вес (кг)
- [ ] Шаг 4: Цена за кг
- [ ] Шаг 5: Подтверждение
- [ ] Каждый шаг: кнопка "Назад"

---

## 13. Рейтинги

- [ ] FSM для оценки: 1-5 звёзд (inline кнопки)
- [ ] Текст отзыва — опционально
- [ ] Нельзя оценить дважды одну доставку
- [ ] Средний рейтинг пересчитывается после каждой оценки
- [ ] Рейтинг отображается в профиле и в карточке попутчика

---

## 14. Vue WebApp проверки

- [ ] Компоненты компилируются без ошибок
- [ ] API запросы обрабатывают ошибки (try/catch)
- [ ] Loading states показываются при загрузке данных
- [ ] Empty states для пустых списков
- [ ] Telegram WebApp SDK инициализирован
- [ ] `initData` отправляется в backend для авторизации
- [ ] Responsive на мобильных устройствах
- [ ] Bottom navigation работает корректно
- [ ] Роутинг между экранами (vue-router) корректен

---

## 15. Финальные проверки перед коммитом

- [ ] `git status` — проверить ВСЕ файлы (нет ли забытых)
- [ ] `git diff` — просмотреть все изменения
- [ ] Нет секретов в коде (.env, токены, ключи)
- [ ] Нет `print()`, `console.log()` для дебага
- [ ] Нет закомментированного кода (удалить или раскомментировать)
- [ ] Комментарии актуальны (не врут)
- [ ] Commit message по формату: `feat:`, `fix:`, `docs:` и т.д.

---

## Быстрый чек-лист (копировать в ответ)

```
### Проверка задачи:
- [ ] UX: Dead-End (callback grep), State Leak, "Назад" кнопки
- [ ] UX: ScreenManager, пустые состояния, пагинация
- [ ] Код: py_compile, circular imports, новые файлы в router
- [ ] Код: аргументы функций, callback конфликты
- [ ] FSM: контекст навигации, очистка state, кнопка "Отмена"
- [ ] БД: commit() не забыт, миграция корректна, один Alembic head
- [ ] Безопасность: escape HTML, edge cases (bot blocked, API error)
- [ ] Telegram: callback_data <= 64 байт, текст <= 4096
- [ ] Логирование: [MODULE] prefix, контекст, правильный уровень
- [ ] Хардкод: тексты через locale, значения из конфига/БД
- [ ] Единые системы: ScreenManager, Locale, API Client, Pinia
- [ ] Relay/Платежи: логирование, контакты скрыты, подтверждение оплаты
- [ ] Финал: git status, git diff, нет secrets, нет print()
- [ ] Enterprise: миграции, rate limiting, refresh token, auth_date
- [ ] Enterprise: нет mock-данных, нет TODO, нет сырых locale ключей
- [ ] Enterprise: navigation guards, error handling, RedisStorage
```

---

## 16. Enterprise-уровень — сравнение с крупными компаниями

> Проект ОБЯЗАН соответствовать стандартам, принятым в крупных компаниях.

| Практика | Стандарт | Требование |
|----------|----------|------------|
| ORM + Migrations | SQLAlchemy + Alembic | Миграции ОБЯЗАТЕЛЬНЫ для каждого изменения схемы БД |
| API Layer (REST) | FastAPI + Pydantic | Тонкие endpoints, валидация, документация |
| Auth (JWT + HMAC) | Telegram initData → HMAC-SHA256 → JWT | access + refresh tokens, проверка auth_date |
| State Management | Pinia (Vue) / RedisStorage (bot) | Единое хранилище, НЕ mock-данные |
| i18n | vue-i18n / locale system | ВСЕ ключи должны существовать, НЕ рендерить сырые ключи |
| Rate Limiting | slowapi / nginx | ОБЯЗАТЕЛЬНО на auth, POST endpoints |
| Monitoring/Logging | Structured logging | [MODULE] prefix, контекст, уровни |
| CI/CD | GitHub Actions / GitLab CI | Автоматизация тестов и деплоя |
| Tests | pytest + vitest + coverage | Unit, интеграционные, E2E тесты |
| Error Tracking | Sentry | Отслеживание ошибок в production |
| WebSocket/SSE | Real-time chat | Для чатов и уведомлений в реальном времени |
| DB Backups | pg_dump cron / WAL streaming | Автоматические бэкапы |
| Health Checks | /health endpoint | Мониторинг доступности сервисов |
| API Docs | Swagger/OpenAPI | Автогенерация документации |
| Secret Management | .env (минимум), Vault (продакшен) | Секреты НИКОГДА в коде |

### Чек-лист enterprise-стандартов:
- [ ] Alembic миграции созданы для ВСЕХ таблиц
- [ ] Rate limiting настроен на всех POST endpoints и auth
- [ ] Refresh token endpoint существует и работает
- [ ] auth_date проверяется (replay-атаки невозможны)
- [ ] JWT type проверяется (refresh != access)
- [ ] Navigation guards в Vue Router (protected routes)
- [ ] ВСЕ locale ключи существуют (нет сырых ключей в UI)
- [ ] НЕТ mock-данных в production views
- [ ] НЕТ TODO/FIXME заглушек в production коде
- [ ] Error handling на ВСЕХ service вызовах (try/except + user feedback)
- [ ] RedisStorage для FSM (не MemoryStorage)
- [ ] ScreenManager slots в Redis (не in-memory dict)
- [ ] Health checks для всех сервисов в docker-compose
- [ ] Нет дефолтных секретных ключей в config

## 17. Аудит — типичные ошибки (выявлены при проверке)

### 17.1 Bot — критические проблемы
- [ ] ВСЕ кнопки меню имеют обработчики (найти попутчика, чаты, заявки, подписка)
- [ ] Кнопки "Назад" в FSM работают (back:weight, back:price, back:photo)
- [ ] try/except на ВСЕХ вызовах сервисов в handlers
- [ ] Locale ключи для клавиатур (НЕ использовать other_city для веса/цены)
- [ ] settings_title БЕЗ HTML тегов и лишних эмодзи в ReplyKeyboard
- [ ] НЕТ хардкод строк на русском в handlers (все через t())
- [ ] MemoryStorage заменён на RedisStorage
- [ ] _slots ScreenManager перенесены в Redis
- [ ] RatingStates используется (flow оценки реализован)

### 17.2 Backend — критические проблемы
- [ ] HMAC: правильный порядок аргументов hmac.new()
- [ ] JWT: проверка type (access vs refresh)
- [ ] auth_date: отклонять initData старше 5 минут
- [ ] POST /auth/refresh endpoint существует
- [ ] Cities endpoint на /api/v1/cities (НЕ /api/v1/users/)
- [ ] GET /flights/{id} endpoint существует
- [ ] Match/Request API полностью реализован
- [ ] Payments/Subscriptions API полностью реализован
- [ ] parcel_service: accept_parcel, update_status, get_for_traveler
- [ ] N+1 queries исправлены в chats
- [ ] Batch UPDATE для read receipts
- [ ] slowapi rate limiting настроен
- [ ] Нет unused imports
- [ ] Deprecated on_event заменён на lifespan

### 17.3 WebApp — критические проблемы
- [ ] НЕТ mock-данных в views (все через API)
- [ ] НЕТ TODO заглушек
- [ ] ВСЕ locale ключи существуют (~45 отсутствующих)
- [ ] Navigation guards (protected routes)
- [ ] fetchMe() вызывается при повторном входе
- [ ] Error states в КАЖДОМ view
- [ ] CityPicker использует API и текущий locale
- [ ] chats store: error handling, try/catch
- [ ] Token refresh mechanism в API client

---

*Последнее обновление: 2026-07-03 (обновлено после аудита)*
