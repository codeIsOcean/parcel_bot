# Контракт: Бот vs Mini App

**Решение владельца (2026-09-07): Mini App-first.** Вся операционка живёт в приложении.
Бот — тонкая обёртка из того, что в Mini App сделать нельзя или неудобно.

## Что делает бот

| Задача | Где в коде |
|---|---|
| Вход `/start [payload]`, онбординг: язык → телефон (Telegram `contact`) | `bot/handlers/start.py` |
| Кнопка «Открыть приложение» (inline web_app, с диплинком на экран) | `bot/keyboards/webapp_kb.py` |
| Уведомления с кнопкой на нужный экран | `backend/app/services/notification_service.py` |
| Приём оплаты Telegram Stars (`pre_checkout`, `successful_payment`) | `bot/handlers/payments.py` |
| Ответы поддержки из Telegram (`/support_queue`, кнопка «Ответить») | `bot/handlers/support_admin.py` |
| Реестр групп: бота добавили/выгнали (`my_chat_member`) | `bot/handlers/groups.py` |
| Команды в группе `/promo_add`, `/promo_off` и подсказка «оформите рейс» | `bot/handlers/promo.py` |
| `/admin` — кнопка в админ-панель приложения | `bot/handlers/start.py` |

**Золотое правило:** бот никогда не даёт кнопок действия (создать, принять, оценить).
Единственная интерактивная кнопка — «Открыть приложение». Reply-меню нет, FSM-сценариев
посылок и рейсов нет. Лишние сообщения в личке перехватывает `bot/middlewares/gate.py`
(белый список: команды, контакт, оплата, состояния онбординга/ответа поддержки).

## Что живёт в Mini App

Посылки, рейсы, поиск попутчиков, отклики, чаты, отслеживание, оценки и ответы
на отзывы, профиль, кабинет и оплата (Stars/TON), поддержка, админ-панель.

## Телефон

Номер обязателен. Два пути, оба через бота (только он может получить `contact`):
1. `/start` → бот просит контакт reply-кнопкой.
2. В приложении без номера показывается `PhoneGate` (`webapp/src/components/shared/PhoneGate.vue`):
   `Telegram.WebApp.requestContact()` → контакт уходит боту → бот сохраняет (`on_contact`) →
   приложение опрашивает `/users/me`. Запасная кнопка открывает бота.

Публичный профиль телефон не отдаёт (`UserProfile`), свой — отдаёт (`PrivateProfile`, `/users/me`).

## Диплинки — один словарь на всех

`shared/deeplinks.py` ⇄ `webapp/src/utils/deeplinks.js`. Параметр `parcel_12`, `flight_7`,
`profile_3`, `chat_9`, `publish`, `requests`, `admin`, `admin_groups`...

| Откуда | Формат | Кто разбирает |
|---|---|---|
| Кнопка в группе | `https://t.me/<bot>?startapp=parcel_12` | Mini App: `start_param` → `resolveStartScreen` в `App.vue` |
| Уведомление в личке | web_app URL `https://<app>/parcels/12` | роутер приложения |
| Ссылка в личку бота | `/start parcel_12` | бот: `pending_param` → после регистрации кнопка web_app на экран |

⚠️ Для `?startapp=` у бота в BotFather должно быть настроено **Main Mini App**
(`/mybots → Bot Settings → Configure Mini App`), иначе ссылка откроет чат бота.
Запасной путь `?start=` работает всегда.

## Режимы «Отправить» / «Перевезти»

Свободное переключение на главной (у попутчиков барьера нет: сегодня везу, завтра отправляю).
Выбор запоминается на сервере (`PUT /users/me {role}`) и восстанавливается при входе.
Перед первой публикацией рейса показывается вводный экран про дневной тариф (один раз, localStorage).
