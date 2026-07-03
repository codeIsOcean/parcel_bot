# WEB Чек-лист — Parcel Bot (Vue 3 + FastAPI)

> **Использование:** При разработке и проверке веб-части проекта (Mini App + Backend API).
> Основан на WEB_CHECKLIST из модер-бота и kividi goods tracker.

---

## 1. Философия

- Профессиональная разработка, никаких костылей
- Код должен быть читаемым, поддерживаемым, тестируемым
- Mobile-first (Telegram Mini App = мобильное устройство)
- Единые системы: один API client, один state manager, один UI kit

---

## 2. Архитектура

### 2.1 Backend (FastAPI)

```
backend/
├── app/
│   ├── main.py              # Точка входа FastAPI
│   ├── config.py             # Конфигурация (.env)
│   ├── dependencies.py       # DI (session, redis, auth)
│   ├── routers/              # Тонкие endpoints
│   │   ├── auth.py
│   │   ├── parcels.py
│   │   ├── flights.py
│   │   ├── chats.py
│   │   ├── users.py
│   │   ├── ratings.py
│   │   └── subscriptions.py
│   ├── services/             # Бизнес-логика
│   ├── schemas/              # Pydantic модели (Request/Response)
│   ├── models/               # SQLAlchemy модели (shared с ботом)
│   └── utils/                # Утилиты
├── requirements.txt
└── Dockerfile
```

### 2.2 Frontend (Vue 3 + Vite)

```
webapp/
├── src/
│   ├── main.js               # Точка входа
│   ├── App.vue               # Root компонент
│   ├── router/               # Vue Router
│   │   └── index.js
│   ├── stores/               # Pinia stores
│   │   ├── auth.js
│   │   ├── parcels.js
│   │   ├── flights.js
│   │   └── chats.js
│   ├── api/                  # API client (axios)
│   │   ├── client.js         # Единый axios instance
│   │   ├── parcels.js
│   │   ├── flights.js
│   │   ├── chats.js
│   │   └── users.js
│   ├── components/           # Переиспользуемые компоненты
│   │   ├── ui/               # UI kit (Button, Input, Card, Modal)
│   │   ├── layout/           # Layout (BottomNav, Header, BackButton)
│   │   └── shared/           # Общие (TravelerCard, ParcelCard, RatingStars)
│   ├── views/                # Страницы (экраны)
│   │   ├── HomeView.vue
│   │   ├── TravelersView.vue
│   │   ├── SendParcelView.vue
│   │   ├── PublishFlightView.vue
│   │   ├── ChatView.vue
│   │   ├── ChatListView.vue
│   │   ├── TrackingView.vue
│   │   ├── ProfileView.vue
│   │   ├── SubscriptionView.vue
│   │   ├── SettingsView.vue
│   │   └── NotificationsView.vue
│   ├── composables/          # Vue 3 Composables (useAuth, useTelegram)
│   ├── locale/               # i18n (ru.json, en.json)
│   ├── utils/                # Утилиты
│   └── assets/               # Стили, иконки
├── index.html
├── vite.config.js
├── package.json
└── Dockerfile
```

### Принципы:
- [ ] Backend: тонкие routers (<= 25 строк на endpoint), логика в services
- [ ] Frontend: переиспользуемые компоненты, composables для логики
- [ ] Shared models: SQLAlchemy модели общие для bot и backend
- [ ] SRP: один файл — одна ответственность

---

## 3. Backend (FastAPI) — чек-лист

### 3.1 Endpoints

- [ ] Тонкие endpoints (получить данные → вызвать service → вернуть результат)
- [ ] Pydantic schemas для Request и Response
- [ ] Dependency Injection: `session = Depends(get_session)`, `user = Depends(get_current_user)`
- [ ] HTTP статус коды: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found
- [ ] Обработка ошибок через `HTTPException`

```python
# ✅ ПРАВИЛЬНО — тонкий endpoint
@router.get("/parcels", response_model=list[ParcelResponse])
async def get_my_parcels(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Получить посылки текущего пользователя."""
    # Вызываем сервис
    parcels = await parcel_service.get_by_user(session, user.id, page, limit)
    return parcels

# ❌ НЕПРАВИЛЬНО — логика в endpoint
@router.get("/parcels")
async def get_my_parcels(user: User = Depends(get_current_user)):
    async with SessionLocal() as session:  # НЕ через DI
        result = await session.execute(
            select(Parcel).where(Parcel.sender_id == user.id)  # Логика в endpoint
        )
        parcels = result.scalars().all()
        return [{"id": p.id, "weight": p.weight} for p in parcels]  # Ручная сериализация
```

### 3.2 Pydantic schemas

- [ ] Request schema (что приходит от клиента): `ParcelCreate`, `FlightCreate`
- [ ] Response schema (что возвращаем): `ParcelResponse`, `FlightResponse`
- [ ] Валидация полей: `Field(ge=0.1, le=50)` для веса, `Field(min_length=3)` для описания
- [ ] Optional поля с дефолтами

### 3.3 Логирование

- [ ] Каждый endpoint логирует вход: `logger.info("[API] GET /parcels: user=%s", user.id)`
- [ ] Результат: `logger.info("[API] Returned %d parcels", len(parcels))`
- [ ] Ошибки: `logger.error("[API] Error: %s", e, exc_info=True)`

### 3.4 Документация (OpenAPI)

- [ ] Каждый endpoint имеет docstring
- [ ] Tags для группировки (`tags=["parcels"]`)
- [ ] `/docs` доступен в dev-режиме

---

## 4. Frontend (Vue 3) — чек-лист

### 4.1 Компоненты

- [ ] Composition API (`<script setup>`)
- [ ] Props с типами и дефолтами
- [ ] Emits явно объявлены
- [ ] Компоненты маленькие (< 200 строк template + script)
- [ ] Переиспользуемые компоненты в `components/ui/` и `components/shared/`

```vue
<!-- ✅ ПРАВИЛЬНО -->
<script setup>
// Пропсы карточки попутчика
const props = defineProps({
  traveler: { type: Object, required: true },
  showPrice: { type: Boolean, default: true },
})

// Событие выбора попутчика
const emit = defineEmits(['select'])
</script>

<template>
  <!-- Карточка попутчика -->
  <div class="traveler-card" @click="emit('select', traveler)">
    <Avatar :name="traveler.name" :rating="traveler.rating" />
    <div class="traveler-info">
      <span class="name">{{ traveler.name }}</span>
      <RatingStars :value="traveler.rating" />
      <span v-if="showPrice" class="price">${{ traveler.price_per_kg }}/кг</span>
    </div>
  </div>
</template>
```

### 4.2 API Client — единый

- [ ] Один axios instance в `api/client.js`
- [ ] Interceptor: автоматическая подстановка JWT токена
- [ ] Interceptor: обработка 401 (redirect на авторизацию)
- [ ] Interceptor: обработка ошибок (toast уведомления)
- [ ] Base URL из конфига (`.env`)

```javascript
// api/client.js
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

// Единый API клиент
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 10000,
})

// Interceptor: JWT токен
api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// Interceptor: обработка ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
    }
    return Promise.reject(error)
  }
)

export default api
```

### 4.3 State Management (Pinia)

- [ ] Stores разделены по доменам: `auth`, `parcels`, `flights`, `chats`
- [ ] Actions для API вызовов
- [ ] Getters для вычисляемых данных
- [ ] НЕ дублировать данные между stores

### 4.4 Vue Router

- [ ] Все экраны описаны в `router/index.js`
- [ ] Lazy loading для страниц: `() => import('@/views/ChatView.vue')`
- [ ] Navigation guard: проверка авторизации
- [ ] Scroll behavior: `savedPosition` или `top`

### 4.5 Composables

- [ ] `useAuth()` — авторизация, текущий пользователь
- [ ] `useTelegram()` — Telegram WebApp SDK (initData, HapticFeedback, BackButton)
- [ ] `useLocale()` — i18n (текущий язык, переключение, функция t())

---

## 5. API дизайн

### 5.1 REST

- [ ] Версионирование: `/api/v1/...`
- [ ] Ресурсы во множественном числе: `/parcels`, `/flights`, `/users`
- [ ] HTTP методы: GET (чтение), POST (создание), PUT (обновление), DELETE (удаление)
- [ ] Пагинация: `?page=1&limit=20`
- [ ] Фильтрация: `?from_city=Dubai&to_city=Almaty&status=active`
- [ ] Сортировка: `?sort=created_at&order=desc`

### 5.2 Формат ответов

```json
// Список с пагинацией
{
  "items": [...],
  "total": 42,
  "page": 1,
  "limit": 20,
  "pages": 3
}

// Ошибка
{
  "detail": "Parcel not found",
  "code": "NOT_FOUND"
}
```

---

## 6. Безопасность

### 6.1 Авторизация (Telegram)

- [ ] Frontend: `Telegram.WebApp.initData` отправляется в backend
- [ ] Backend: проверка подписи HMAC-SHA256 (BOT_TOKEN)
- [ ] JWT: access token (short-lived, 15 min) + refresh token (7 days)
- [ ] Роли: sender, traveler (или оба)
- [ ] Каждый endpoint проверяет авторизацию через `Depends(get_current_user)`

```python
# ✅ Проверка Telegram initData
import hmac
import hashlib

def verify_telegram_data(init_data: str, bot_token: str) -> dict:
    """Верифицирует initData от Telegram WebApp."""
    # Парсим данные
    parsed = dict(parse_qs(init_data))
    # Извлекаем hash
    received_hash = parsed.pop("hash")[0]
    # Формируем строку для проверки
    data_check_string = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )
    # HMAC-SHA256
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    # Сравниваем
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(401, "Invalid Telegram data")
    return parsed
```

### 6.2 Защита

- [ ] CORS: только разрешённые origins (Telegram WebApp домены)
- [ ] Rate limiting: `slowapi` на auth и создание данных
- [ ] Input validation: Pydantic на всех входных данных
- [ ] SQL injection: ТОЛЬКО ORM, НЕ raw SQL
- [ ] XSS: экранирование пользовательского ввода
- [ ] HTTPS: обязательно в production
- [ ] Secrets: ТОЛЬКО в `.env`, НЕ в коде

---

## 7. База данных (общая с ботом)

### 7.1 Общие таблицы

| Таблица | Описание | Бот | API |
|---------|----------|-----|-----|
| users | Пользователи | R/W | R/W |
| parcels | Посылки | R/W | R/W |
| flights | Рейсы перевозчиков | R/W | R/W |
| matches | Совпадения посылка↔рейс | R/W | R |
| relay_messages | Сообщения чата | R/W | R |
| reviews | Отзывы и рейтинги | R/W | R/W |
| subscriptions | Подписки | R/W | R |
| payments | Платежи | R/W | R |
| cities | Города и маршруты | R | R |
| route_votes | Голосование за маршруты | R/W | R/W |

### 7.2 Правила

- [ ] Модели SQLAlchemy в `shared/models/` (общие для bot и backend)
- [ ] Alembic миграции в `alembic/` (один набор для всех)
- [ ] API: read-only для таблиц, где бот — главный writer (payments, subscriptions)
- [ ] Транзакции: `async with session.begin():`
- [ ] Индексы: на user_id, status, from_city, to_city, created_at

---

## 8. Тестирование

### 8.1 Backend (pytest)

- [ ] Unit тесты для services
- [ ] Тесты endpoints через `httpx.AsyncClient`
- [ ] Тестовая БД (SQLite in-memory или отдельный PostgreSQL)
- [ ] Фикстуры для создания тестовых данных
- [ ] `pytest --cov` для покрытия

### 8.2 Frontend (Vitest)

- [ ] Unit тесты для composables
- [ ] Component тесты для UI компонентов
- [ ] Mock для API запросов
- [ ] Mock для Telegram WebApp SDK

### 8.3 E2E (Playwright — опционально)

- [ ] Авторизация flow
- [ ] Создание посылки flow
- [ ] Публикация рейса flow
- [ ] Чат flow

---

## 9. Деплой и инфраструктура

### 9.1 Docker

```yaml
# docker-compose.yml
services:
  bot:
    build: ./bot
    depends_on: [db, redis]
  backend:
    build: ./backend
    depends_on: [db, redis]
    ports: ["8000:8000"]
  webapp:
    build: ./webapp
    ports: ["3000:3000"]
  db:
    image: postgres:16
  redis:
    image: redis:7-alpine
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
```

- [ ] Каждый компонент в отдельном контейнере
- [ ] `docker-compose up` запускает всё
- [ ] Health check для каждого сервиса
- [ ] Volumes для данных БД и Redis
- [ ] `.env` через `env_file`

### 9.2 Nginx

- [ ] Reverse proxy: `/api/` → backend:8000
- [ ] Static files: `/` → webapp build
- [ ] WebSocket proxy (если нужен для чатов)
- [ ] HTTPS (Let's Encrypt / Cloudflare)
- [ ] Gzip compression
- [ ] Correlation ID header

---

## 10. Производительность

- [ ] Redis кэширование: список городов, популярные маршруты
- [ ] Пагинация: ВСЕ списки с limit/offset
- [ ] Lazy loading: `import()` для Vue страниц
- [ ] Debounce: поисковые запросы (300ms)
- [ ] Оптимистичные обновления: рейтинг, избранное
- [ ] Сжатие: gzip для API ответов и static files

---

## 11. UX/UI (Mini App)

### 11.1 Обязательные состояния

Каждый экран ДОЛЖЕН обрабатывать:
- [ ] **Loading** — skeleton/spinner при загрузке данных
- [ ] **Error** — сообщение об ошибке + кнопка "Повторить"
- [ ] **Empty** — подсказка + CTA кнопка (например "Нет посылок. Создать?")
- [ ] **Success** — toast/уведомление при успешном действии

### 11.2 Responsive

- [ ] Mobile-first (Telegram Mini App = мобильный экран)
- [ ] Тестировать на экранах 320px-428px ширины
- [ ] Bottom Navigation не перекрывает контент
- [ ] Scrollable контент, НЕ fixed height

### 11.3 Telegram WebApp SDK

- [ ] `Telegram.WebApp.ready()` — вызвать при загрузке
- [ ] `Telegram.WebApp.expand()` — развернуть на весь экран
- [ ] `Telegram.WebApp.BackButton` — управление кнопкой "Назад"
- [ ] `Telegram.WebApp.MainButton` — кнопка действия внизу экрана
- [ ] `Telegram.WebApp.HapticFeedback` — тактильная обратная связь
- [ ] `Telegram.WebApp.themeParams` — цвета темы Telegram
- [ ] `Telegram.WebApp.colorScheme` — light/dark тема

### 11.4 Цветовая тема

- [ ] Использовать CSS переменные из `Telegram.WebApp.themeParams`
- [ ] Поддержка light и dark theme
- [ ] Fallback цвета если themeParams недоступны

```css
:root {
  /* Telegram theme variables */
  --tg-theme-bg-color: var(--tg-theme-bg-color, #ffffff);
  --tg-theme-text-color: var(--tg-theme-text-color, #000000);
  --tg-theme-hint-color: var(--tg-theme-hint-color, #999999);
  --tg-theme-link-color: var(--tg-theme-link-color, #2481cc);
  --tg-theme-button-color: var(--tg-theme-button-color, #5288c1);
  --tg-theme-button-text-color: var(--tg-theme-button-text-color, #ffffff);
  --tg-theme-secondary-bg-color: var(--tg-theme-secondary-bg-color, #efeff3);
}
```

---

## 12. Локализация (i18n)

- [ ] Файлы: `locale/ru.json`, `locale/en.json`
- [ ] Composable: `useLocale()` с функцией `t(key)`
- [ ] Язык определяется: `Telegram.WebApp.initDataUnsafe.user.language_code`
- [ ] Fallback: если языка нет → русский
- [ ] Переключение языка в настройках
- [ ] ВСЕ тексты через `t()`, НЕ хардкод

```javascript
// composables/useLocale.js
import { ref, computed } from 'vue'
import ru from '@/locale/ru.json'
import en from '@/locale/en.json'

const locales = { ru, en }
const currentLang = ref('ru')

export function useLocale() {
  // Функция перевода
  const t = (key) => {
    return locales[currentLang.value]?.[key] || locales.ru[key] || key
  }

  // Установить язык
  const setLang = (lang) => {
    currentLang.value = locales[lang] ? lang : 'ru'
  }

  return { t, currentLang, setLang }
}
```

---

## 13. Единые системы — сводка

| Система | Файл | Назначение |
|---------|------|-----------|
| API Client | `api/client.js` | Все HTTP запросы |
| Auth Store | `stores/auth.js` | Авторизация, JWT, текущий user |
| Locale | `composables/useLocale.js` | Все тексты i18n |
| Telegram SDK | `composables/useTelegram.js` | WebApp API, BackButton, MainButton |
| UI Kit | `components/ui/` | Button, Input, Card, Modal, Toast |
| Layout | `components/layout/` | BottomNav, Header, BackButton |
| Router | `router/index.js` | Все маршруты приложения |
| Config | `.env` + `vite.config.js` | API URL, feature flags |

**Правило:** Каждая система — в ОДНОМ месте. НЕ дублировать.

---

## 14. Enterprise-уровень — сравнение с крупными компаниями

> Веб-часть проекта ОБЯЗАНА соответствовать стандартам, принятым в крупных компаниях.

| Практика | Стандарт | Статус / Требование |
|----------|----------|---------------------|
| ORM + Migrations | SQLAlchemy + Alembic | Миграции ОБЯЗАТЕЛЬНЫ |
| API Layer (REST) | FastAPI + Pydantic | Тонкие endpoints, DI, документация |
| Auth (JWT + HMAC) | HMAC-SHA256 + JWT | access + refresh, проверка auth_date, type |
| State Management | Pinia | Stores по доменам, actions для API, НЕ mock |
| i18n | useLocale composable | ВСЕ ключи существуют в ru.json/en.json |
| Rate Limiting | slowapi | На auth, POST endpoints |
| CI/CD | GitHub Actions | Автотесты, линтинг, деплой |
| Tests | pytest (backend) + vitest (frontend) | Покрытие > 70% |
| Error Tracking | Sentry | Мониторинг ошибок |
| WebSocket/SSE | FastAPI WebSocket | Real-time чат |
| DB Backups | pg_dump cron / WAL | Автоматические бэкапы |
| Secret Management | .env → Vault (prod) | Секреты НЕ в коде |

---

## 15. Аудит — выявленные проблемы

### 15.1 Backend
- [ ] HMAC: правильный порядок аргументов — `hmac.new(bot_token.encode(), b"WebAppData", ...)`
- [ ] JWT type: access token !== refresh token (проверять payload.type)
- [ ] auth_date: отклонять initData старше 300 секунд
- [ ] POST /auth/refresh: эндпоинт ОБЯЗАТЕЛЕН (JWT expiry 15 min)
- [ ] Cities: отдельный router /api/v1/cities (НЕ на /api/v1/users/)
- [ ] GET /flights/{id}: эндпоинт для детальной страницы
- [ ] Match API: GET/POST /flights/{id}/requests — приём/отклонение посылок
- [ ] Payments API: Telegram Stars webhook + TON verification
- [ ] Subscriptions API: CRUD для подписок
- [ ] parcel_service: accept_parcel(), update_status(), get_for_traveler()
- [ ] N+1 fix: get_my_chats — использовать JOIN вместо N запросов
- [ ] Batch UPDATE: read receipts одним UPDATE, не циклом
- [ ] slowapi: rate limiting на /auth/login и все POST endpoints
- [ ] Deprecated: заменить @app.on_event на lifespan
- [ ] Review guards: проверять что посылка delivered, нет дублей, участник

### 15.2 Frontend (Vue 3)
- [ ] НЕТ mock-данных: ProfileView, TrackingView, TravelersView, ChatView, RateView, HomeView
- [ ] НЕТ TODO заглушек: RateView, SubscriptionView (Stars/TON), SettingsView
- [ ] ~45 locale ключей: добавить все отсутствующие в ru.json и en.json
- [ ] Navigation guards: beforeEach в router — redirect неавторизованных
- [ ] fetchMe(): вызывать при повторном входе (token уже есть в localStorage)
- [ ] Error states: КАЖДЫЙ view обрабатывает ошибки API (не только loading/empty)
- [ ] CityPicker: загружать города из API, показывать на текущем языке
- [ ] Token refresh: interceptor в api/client.js для автоматического обновления JWT
- [ ] chats store: try/catch в fetchMessages и sendMessage
- [ ] Unused imports: удалить во всех views
- [ ] onUnmounted: ChatView — clearInterval для polling
- [ ] haptic feedback: BottomNav tab switch

---

## Быстрый чек-лист (копировать в ответ)

```
### WEB проверка:
- [ ] Backend: тонкий endpoint, Pydantic schema, DI, логирование
- [ ] Frontend: Composition API, props/emits, компоненты < 200 строк
- [ ] API: единый client, interceptors (JWT, errors), base URL из .env
- [ ] State: Pinia store по доменам, actions для API
- [ ] Auth: initData → HMAC-SHA256 → JWT, Depends(get_current_user)
- [ ] Security: CORS, rate limit, input validation, no SQL injection
- [ ] UX: loading/error/empty states, responsive, Telegram SDK
- [ ] i18n: все тексты через t(), locale файлы
- [ ] БД: shared models, Alembic, индексы, commit()
- [ ] Docker: docker-compose up работает, health checks
- [ ] Тесты: pytest backend, vitest frontend
- [ ] Enterprise: нет mock-данных, нет TODO, нет сырых locale ключей
- [ ] Enterprise: HMAC fix, refresh token, auth_date, rate limiting
- [ ] Enterprise: navigation guards, error handling, token refresh
```

---

*Последнее обновление: 2026-07-03 (обновлено после аудита)*
