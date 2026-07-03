# DEVELOPER RULES — Parcel Bot

> Правила разработки и взаимодействия с проектом Parcel Bot.
> Эти правила ОБЯЗАТЕЛЬНЫ для выполнения. НЕ меняй этот файл без согласования.

---

## 1. Архитектура

**НИКОГДА** не меняй архитектуру проекта без явного разрешения.

Проект состоит из 3 компонентов:
- **Bot** — Telegram Bot (aiogram 3, Python)
- **Backend** — FastAPI REST API (Python)
- **WebApp** — Telegram Mini App (Vue 3 + Vite)

Все компоненты используют **общую БД** (PostgreSQL) и **общий Redis**.

```
parcel_bot/
├── bot/           # Telegram Bot (aiogram 3)
├── backend/       # FastAPI API
├── webapp/        # Vue 3 Mini App
├── shared/        # Общие модели, утилиты, locale
├── docs/          # Документация
├── alembic/       # Миграции БД
└── docker-compose.yml
```

---

## 2. Комментирование кода

Над **КАЖДОЙ** значимой строкой кода — комментарий на русском языке.

**ОБЯЗАТЕЛЬНО** комментировать:
- Handlers (бот)
- Services (бизнес-логика)
- Keyboards (клавиатуры)
- Middleware (промежуточные обработчики)
- API endpoints (FastAPI)
- Vue компоненты (template + script)
- Миграции БД
- Конфигурация

### Python (bot, backend):
```python
# Получаем активные рейсы перевозчика
flights = await flight_service.get_active_by_user(user_id)

# Формируем inline-клавиатуру с рейсами
keyboard = build_flights_keyboard(flights)
```

### Vue 3 (webapp):
```vue
<script setup>
// Загружаем список попутчиков для выбранного маршрута
const travelers = ref([])

// Фильтр: показывать только перевозчиков с рейтингом >= 4
const filteredTravelers = computed(() =>
  travelers.value.filter(t => t.rating >= 4)
)
</script>

<template>
  <!-- Карточка попутчика с рейтингом и ценой -->
  <TravelerCard
    v-for="t in filteredTravelers"
    :key="t.id"
    :traveler="t"
  />
</template>
```

### FastAPI:
```python
@router.post("/parcels")
async def create_parcel(
    data: ParcelCreate,  # Валидация через Pydantic
    user: User = Depends(get_current_user),  # JWT из Telegram initData
    session: AsyncSession = Depends(get_session),  # DI сессия БД
):
    # Создаём посылку через сервис
    parcel = await parcel_service.create(session, user.id, data)
    return parcel
```

---

## 3. Маленькие шаги

Одно действие = один коммит. НЕ делать 5 изменений в одном коммите.

**Правильно:**
- `feat: add parcel creation FSM`
- `feat: add traveler list keyboard`
- `fix: fix city picker back button`

**Неправильно:**
- `update bot` (что обновлено?)
- `fix everything` (что пофикшено?)

---

## 4. Логика — не ломать существующее

Перед изменением рабочей функции:
1. Прочитай текущий код
2. Пойми как он работает
3. Убедись что изменение НЕ сломает другие части
4. Проверь после изменения

**Критичные системы (нельзя ломать):**
- Создание/отслеживание посылок
- Публикация рейсов
- Relay-чат между пользователями
- Оплата подписки (Stars/TON)
- Рейтинги и отзывы
- FSM диалоги (пошаговые сценарии)
- Авторизация (Telegram initData → JWT)

---

## 4.1 Edge Cases & Fallback — КРИТИЧНО!

**КАЖДАЯ** функция должна обрабатывать edge cases:

| Сценарий | Что делать |
|----------|-----------|
| Пользователь заблокировал бота | `try/except TelegramForbiddenError` — пометить `user.bot_blocked = True` |
| Telegram API вернул ошибку | Retry с backoff, логировать |
| Платёж Stars не прошёл | Показать ошибку, НЕ активировать подписку |
| TON транзакция pending | Показать "Ожидание подтверждения", проверять по cron |
| Пользователь нажал кнопку дважды | Идемпотентность — проверить текущее состояние |
| FSM state потерян (Redis restart) | Graceful fallback — показать главное меню |
| Фото посылки не загрузилось | Разрешить повторную отправку, НЕ терять остальные данные FSM |
| Relay-чат: получатель заблокировал бота | Уведомить отправителя "Пользователь недоступен" |
| БД недоступна | Graceful degradation, НЕ крашить бота |
| Пустой список попутчиков | Показать "Нет попутчиков на этом маршруте", НЕ пустой экран |

---

## 5. Тесты

### 5.1 Unit-тесты
- Бизнес-логика (services): создание посылки, расчёт рейтинга, проверка подписки
- Валидация данных (Pydantic schemas)
- Утилиты (парсинг дат, форматирование цен)

### 5.2 Интеграционные тесты
- Handler → Service → БД (полный путь)
- API endpoint → Service → БД
- FSM переходы состояний

### 5.3 E2E тесты
- Полный flow: создание посылки → поиск попутчика → чат → доставка → рейтинг

### Правила:
```python
# ✅ ПРАВИЛЬНО — тестовая БД
@pytest.fixture
async def session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as s:
        yield s

# ❌ НЕПРАВИЛЬНО — боевая БД
session = SessionLocal()  # НИКОГДА не использовать prod БД в тестах!
```

---

## 6. Документация

**ВСЕГДА** обновлять документацию при изменении:
- `docs/ARCHITECTURE.md` — структура проекта, компоненты
- `docs/DATABASE.md` — модели, таблицы, связи
- `docs/API.md` — FastAPI endpoints
- `docs/CHECKLIST.md` — чек-лист проверки
- `docs/WEB_CHECKLIST.md` — чек-лист веб-части

---

## 7. Не выдумывать ограничения

Если не уверен — спроси. НЕ додумывай за пользователя.

❌ "Это невозможно сделать в Telegram"
✅ "Я проверю документацию Telegram Bot API"

❌ "Vue не поддерживает это"
✅ "Покажу рабочий пример"

---

## 8. Уточняющие вопросы

Если задача неясна — **СПРОСИ** перед началом работы.

Лучше потратить 1 минуту на вопрос, чем 30 минут на неправильную реализацию.

---

## 9. Проверка на ошибки

После **КАЖДОГО** изменения:
1. `python -m py_compile file.py` — синтаксис Python
2. Проверить импорты — нет circular imports
3. Проверить что бот запускается
4. Проверить что API endpoint отвечает
5. Проверить Vue компоненты — нет ошибок в консоли

```bash
# Проверка circular imports
python -c "from bot.handlers import main_router"
python -c "from backend.app.main import app"
```

---

## 10. Минимальные патчи

**НЕ** переписывать файлы целиком. Меняй только то, что нужно.

❌ Переписал весь файл handlers/parcel.py (500 строк) ради одного фикса
✅ Изменил 3 строки в нужной функции

---

## 11. ЗАПРЕТ ХАРДКОДА

**ВСЕ** значения из конфига, НЕ из кода.

```python
# ❌ НЕПРАВИЛЬНО
SUBSCRIPTION_PRICE = 40  # захардкожено
CITIES = ["Dubai", "Almaty", "Moscow"]  # захардкожено

# ✅ ПРАВИЛЬНО
SUBSCRIPTION_PRICE = config.subscription.monthly_price  # из конфига
CITIES = await city_service.get_all(session)  # из БД
```

**Исключения:** только технические константы (HTTP коды, Telegram лимиты).

---

## 12. Логирование действий

Все значимые действия логируются с контекстом:

```python
# ✅ ПРАВИЛЬНО — полный контекст
logger.info(
    "[PARCEL] Посылка создана: parcel_id=%s, sender=%s, route=%s→%s, weight=%sкг",
    parcel.id, user.id, parcel.from_city, parcel.to_city, parcel.weight
)

logger.info(
    "[PAYMENT] Подписка оплачена: user=%s, plan=%s, method=%s, amount=%s",
    user.id, plan.name, payment_method, amount
)

# ❌ НЕПРАВИЛЬНО — нет контекста
logger.info("Посылка создана")
logger.info("Оплата прошла")
```

### Префиксы модулей:
| Модуль | Префикс |
|--------|---------|
| Посылки | `[PARCEL]` |
| Рейсы | `[FLIGHT]` |
| Relay-чат | `[RELAY]` |
| Оплата | `[PAYMENT]` |
| Подписки | `[SUBSCRIPTION]` |
| Рейтинги | `[RATING]` |
| Авторизация | `[AUTH]` |
| FSM | `[FSM]` |
| ScreenManager | `[SCREEN]` |
| WebApp API | `[API]` |

---

## 13. Git Commit Conventions

```
feat: новая функциональность
fix: исправление бага
docs: документация
refactor: рефакторинг без изменения поведения
test: добавление тестов
chore: конфигурация, зависимости
perf: оптимизация производительности
```

**ЗАПРЕЩЕНО** упоминать Claude/AI в коммитах.

---

## 14. Database Migrations (Alembic)

### Перед созданием миграции:
```bash
# Проверить что нет расхождений HEAD
alembic heads
# Должен быть ОДИН head
```

### Правила:
- Уникальные revision ID (НЕ копировать из старых)
- ENUM: создавать идемпотентно (`IF NOT EXISTS`)
- Каждая миграция — откатываемая (`downgrade()` обязателен)
- Проверять на пустой БД: `alembic upgrade head`

```python
# ✅ ПРАВИЛЬНО — идемпотентный ENUM
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Создаём enum только если не существует
    parcel_status = sa.Enum('pending', 'accepted', 'in_transit', 'delivered', 'cancelled',
                            name='parcelstatus', create_type=False)
    parcel_status.create(op.get_bind(), checkfirst=True)
```

---

## 15. Security Checklist

- [ ] Input Validation — все входные данные валидируются (Pydantic)
- [ ] Secrets — токены, ключи ТОЛЬКО в `.env`, НИКОГДА в коде
- [ ] Telegram initData — ВСЕГДА проверять подпись (HMAC-SHA256)
- [ ] SQL Injection — ТОЛЬКО ORM запросы, НЕ raw SQL
- [ ] XSS — экранирование HTML в Telegram (`&lt;`, `&gt;`)
- [ ] Rate Limiting — на API endpoints (slowapi)
- [ ] CORS — только разрешённые origins
- [ ] JWT — ротация токенов, short-lived access + refresh
- [ ] Relay-чат — контакты скрыты до подтверждения обеими сторонами
- [ ] Платежи — верифицировать через Telegram API, НЕ доверять клиенту

---

## 16. Naming Conventions

| Тип | Формат | Пример |
|-----|--------|--------|
| Переменные, функции | `snake_case` | `get_active_flights` |
| Классы | `PascalCase` | `ParcelService` |
| Константы | `UPPER_SNAKE` | `MAX_PARCEL_WEIGHT` |
| Vue компоненты | `PascalCase` | `TravelerCard.vue` |
| Vue composables | `camelCase` с use | `useAuth.js` |
| API endpoints | `kebab-case` | `/api/v1/my-parcels` |
| БД таблицы | `snake_case` | `relay_messages` |
| Callback data | `snake_case` с `:` | `parcel:create:confirm` |

---

## 17. Error Handling

```python
# ❌ НИКОГДА не глушить ошибки
try:
    await do_something()
except Exception:
    pass  # ЗАПРЕЩЕНО!

# ✅ ПРАВИЛЬНО — логировать и обрабатывать
try:
    await do_something()
except TelegramForbiddenError:
    # Пользователь заблокировал бота
    logger.warning("[BOT] User %s blocked bot", user_id)
    await user_service.mark_bot_blocked(session, user_id)
except Exception as e:
    logger.error("[BOT] Unexpected error: %s", e, exc_info=True)
    # Graceful degradation — показать пользователю сообщение об ошибке
```

---

## 18. Разделение Handlers и Services — MUST!

**Handlers** — тонкие (<=25 строк), только:
- Получить данные из update/message
- Вызвать service
- Отправить ответ через ScreenManager

**Services** — вся бизнес-логика:
- Работа с БД
- Валидация
- Расчёты
- Внешние API

```python
# ❌ НЕПРАВИЛЬНО — логика в handler
@router.message(ParcelStates.confirm)
async def confirm_parcel(message: Message, state: FSMContext):
    data = await state.get_data()
    parcel = Parcel(
        sender_id=message.from_user.id,
        from_city=data["from_city"],
        to_city=data["to_city"],
        weight=data["weight"],
        price=data["price"],
    )
    session.add(parcel)
    await session.commit()
    # ... ещё 30 строк логики

# ✅ ПРАВИЛЬНО — логика в service
@router.message(ParcelStates.confirm)
async def confirm_parcel(message: Message, state: FSMContext, session: AsyncSession):
    # Получаем данные из FSM
    data = await state.get_data()
    # Создаём посылку через сервис
    parcel = await parcel_service.create(session, message.from_user.id, data)
    # Очищаем FSM
    await state.clear()
    # Показываем результат
    await screen.show(message.from_user.id, format_parcel_created(parcel), slot="main")
```

---

## 19. SRP (Single Responsibility Principle)

| Размер файла | Статус |
|-------------|--------|
| < 300 строк | ✅ OK |
| 300-500 строк | ⚠️ Следить |
| 500-800 строк | 🟡 Рефакторить при возможности |
| > 800 строк | 🔴 КРИТИЧНО — разбить немедленно |

---

## 20. ScreenManager — единая система UI сообщений

**ВСЕ** сообщения бота отправляются через ScreenManager. НЕ использовать `message.answer()` напрямую.

### Слоты:
- `main` — основное сообщение с ReplyKeyboard (одно на экран)
- `inline` — сообщение с InlineKeyboard (детали, действия)
- `temp` — временное сообщение (уведомления, авто-удаление)

```python
# ❌ НЕПРАВИЛЬНО — напрямую
await message.answer("Выберите город", reply_markup=keyboard)

# ✅ ПРАВИЛЬНО — через ScreenManager
await screen.show(
    chat_id=user_id,
    text="Выберите город отправления:",
    slot="main",
    reply_markup=cities_keyboard
)
```

**Почему:** ScreenManager автоматически удаляет предыдущее сообщение в слоте, предотвращает message clutter, управляет историей навигации.

---

## 21. FSM — правила работы с состояниями

### Обязательная очистка:
```python
# ✅ При завершении FSM — ВСЕГДА очищать state
await state.clear()

# ✅ При отмене — очищать state И показывать меню
await state.clear()
await screen.show(user_id, "Главное меню", slot="main", reply_markup=main_menu_kb)
```

### State Leak Prevention:
- Каждый FSM flow должен иметь выход (кнопка "Отмена")
- При ошибке — очищать state, показывать меню
- НЕ оставлять пользователя в "подвешенном" состоянии

### Контекст навигации:
```python
# ✅ Сохранять контекст для кнопки "Назад"
await state.update_data(
    section="create_parcel",     # текущий раздел
    step=3,                       # текущий шаг
    bot_message_id=msg.message_id # ID сообщения для edit
)
```

---

## 22. ЗАПРЕТ Dead-End UX

Пользователь **ВСЕГДА** должен иметь путь назад или выход.

- [ ] Каждый экран имеет кнопку "Назад" или "Отмена"
- [ ] Каждый `callback_data` имеет handler
- [ ] Ошибки показывают что делать дальше
- [ ] Пустые списки показывают подсказку ("Нет посылок. Создать?")
- [ ] Timeout в FSM возвращает в меню

### Проверка:
```bash
# Найти все callback_data в коде
grep -rn "callback_data=" bot/keyboards/ | grep -oP "callback_data=['\"]([^'\"]+)" | sort -u

# Найти все callback handlers
grep -rn "CallbackQuery.*data\." bot/handlers/ | sort -u

# Сравнить — каждый callback_data должен иметь handler!
```

---

## 23. ЗАПРЕТ "короткого пути"

**НЕ** тестировать через прямое создание в БД. **ТОЛЬКО** через UI flow.

```python
# ❌ НЕПРАВИЛЬНО — создание напрямую
parcel = Parcel(sender_id=1, from_city="Dubai", to_city="Almaty")
session.add(parcel)

# ✅ ПРАВИЛЬНО — через UI flow
# Отправить /send → выбрать город → описание → вес → фото → цена → подтвердить
```

---

## 24. HTML экранирование в Telegram

```python
from html import escape

# ✅ ПРАВИЛЬНО
text = f"Посылка от <b>{escape(user.name)}</b>"

# ❌ НЕПРАВИЛЬНО — XSS через имя пользователя
text = f"Посылка от <b>{user.name}</b>"
```

---

## 25. CPU-heavy операции

**НЕ** блокировать Event Loop. Используй `run_in_executor` для тяжёлых операций.

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

# ✅ Обработка фото в отдельном потоке
result = await asyncio.get_event_loop().run_in_executor(
    executor, process_image, photo_bytes
)
```

---

## 26. НЕ менять поведение без согласия — MUST!

**НИКОГДА** не меняй бизнес-логику "для улучшения" без явного согласия.

Примеры **ЗАПРЕЩЁННЫХ** действий:
- Изменить порядок шагов в FSM
- Поменять формат отображения цен
- Изменить логику матчинга посылок и рейсов
- Поменять условия подписки
- Изменить relay-чат поведение

---

## 27. Git Commit — проверка новых файлов

Перед коммитом:
```bash
git status  # Проверить ВСЕ новые файлы
git diff --cached  # Проверить что коммитится
```

**Один пропущенный файл = приложение падает.**

---

## 28. Locale — единая система локализации

**ВСЕ** тексты пользователю — через систему локализации. НЕ хардкодить строки.

```python
# ❌ НЕПРАВИЛЬНО
await screen.show(user_id, "Выберите город")

# ✅ ПРАВИЛЬНО
await screen.show(user_id, t(user.lang, "choose_city"))
```

Поддерживаемые языки: `ru`, `en`, `kz`

Файлы локализации: `shared/locale/{lang}.json`

---

## 29. Единые системы проекта

| Система | Назначение | Одна на весь проект |
|---------|-----------|-------------------|
| ScreenManager | Отправка UI сообщений в боте | ✅ |
| Locale (i18n) | Все тексты пользователю | ✅ |
| AuthService | Авторизация (Telegram → JWT) | ✅ |
| ParcelService | Работа с посылками | ✅ |
| FlightService | Работа с рейсами | ✅ |
| RelayService | Relay-чат | ✅ |
| PaymentService | Оплата Stars/TON | ✅ |
| RatingService | Рейтинги и отзывы | ✅ |
| NotificationService | Push-уведомления | ✅ |
| Config | Конфигурация (.env) | ✅ |
| Logger | Логирование с префиксами | ✅ |
| API Client (Vue) | HTTP запросы к backend | ✅ |
| Store (Pinia) | State management (Vue) | ✅ |

**Правило:** Одна система = одна задача. НЕ дублировать логику.

---

## 30. Роль AI — Senior Developer / Tech Lead

AI должен думать как **Tech Lead**, а не как исполнитель:
- Предлагать решения, а не молчать
- Видеть архитектурные проблемы заранее
- Предупреждать о потенциальных багах
- Следить за качеством кода в целом
- Помнить о единых системах

---

## 31. Relay-чат — правила

- Сообщения проходят **ТОЛЬКО** через бота (RelayService)
- Контакты скрыты до подтверждения **обеими** сторонами
- Каждое сообщение логируется: `[RELAY] from=%s to=%s parcel=%s`
- При блокировке бота одной стороной — уведомить другую
- TTL чата — настраиваемый (по умолчанию активен пока посылка в статусе active)

---

## 32. Подписки и платежи — правила

- **НИКОГДА** не активировать подписку без подтверждения оплаты
- Stars: верифицировать через `pre_checkout_query` → `successful_payment`
- TON: проверять транзакцию через TON API
- Логировать **ВСЕ** платежи: `[PAYMENT] user=%s amount=%s method=%s status=%s`
- Напоминание за 3 дня до окончания подписки
- Graceful блокировка при неоплате (НЕ удалять данные, только ограничить функции)

---

## 33. Callback data — формат

```python
# Формат: module:action:id
# Пример: parcel:view:123, flight:accept:456, rating:set:5

# ❌ НЕПРАВИЛЬНО — нечитаемо
callback_data = "p_v_123"
callback_data = "action_1_flight_accept_456_confirm"  # > 64 байт!

# ✅ ПРАВИЛЬНО — читаемо и компактно
callback_data = "parcel:view:123"
callback_data = "flight:accept:456"
callback_data = "rate:5:parcel:123"
```

**Лимит:** callback_data <= 64 байта. Проверять!

---

## 34. Telegram лимиты

| Параметр | Лимит |
|----------|-------|
| callback_data | <= 64 байта |
| Текст сообщения | <= 4096 символов |
| Caption | <= 1024 символа |
| Текст кнопки | <= 64 символа |
| Inline кнопок в строке | <= 8 |
| Строк кнопок | <= 100 |
| Файл | <= 50 MB |
| Фото | <= 10 MB |

---

## 35. ФИКСИТЬ КОРЕНЬ, А НЕ СИМПТОМ

Перед фиксом — проследить **ВЕСЬ путь данных**.

```
❌ "Рейтинг показывает 0" → добавить `or 0` в шаблон
✅ "Рейтинг показывает 0" → проверить: БД → Service → API → Frontend → отрисовка
   → Найти где именно теряются данные
```

---

## 36. Enterprise-стандарты — ОБЯЗАТЕЛЬНО!

Проект ОБЯЗАН соответствовать стандартам, принятым в крупных компаниях.

| Практика | Стандарт | Требование |
|----------|----------|------------|
| ORM + Migrations | SQLAlchemy + Alembic | Миграция для КАЖДОГО изменения схемы |
| API Layer | FastAPI + Pydantic | Тонкие endpoints, DI, валидация |
| Auth | HMAC-SHA256 + JWT | access + refresh, проверка auth_date и type |
| State Management | Pinia (Vue) / RedisStorage (bot) | Единое хранилище, НЕ MemoryStorage |
| i18n | Locale system | ВСЕ ключи существуют, НЕ хардкод |
| Rate Limiting | slowapi / nginx | На auth и POST endpoints |
| Logging | Structured logging | [MODULE] prefix, контекст, уровни |
| CI/CD | GitHub Actions | Автотесты, линтинг, деплой |
| Tests | pytest + vitest | Unit, интеграционные, E2E |
| Error Tracking | Sentry | Мониторинг ошибок в production |
| Real-time | WebSocket/SSE | Для чатов и уведомлений |
| DB Backups | pg_dump / WAL | Автоматические бэкапы |
| Health Checks | /health endpoint | Мониторинг доступности |
| API Docs | Swagger/OpenAPI | Автогенерация |
| Secrets | .env → Vault (prod) | НИКОГДА в коде |

### Запрещено в production-коде:
- Mock-данные и заглушки (`setTimeout` вместо API, хардкод объекты)
- `TODO` / `FIXME` комментарии (всё должно быть реализовано)
- Сырые locale ключи (все keys должны существовать в JSON)
- `MemoryStorage` для FSM (только RedisStorage)
- In-memory хранение состояния (ScreenManager slots → Redis)
- Дефолтные секретные ключи (`"change-me-in-production"`)
- Отсутствие error handling на service вызовах

---

## 37. Message Clutter — чистка сообщений

- Использовать `edit_text` вместо `answer` для inline callbacks
- ScreenManager автоматически удаляет старые сообщения в слоте
- Временные сообщения (slot="temp") — авто-удаление через N секунд
- НЕ оставлять "мусор" в чате

---

*Последнее обновление: 2026-07-03*
