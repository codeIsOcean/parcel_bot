"""Тексты уведомлений, общие для бота и бэкенда.

Лежат в shared, потому что уведомления шлёт бэкенд, а бот тоже должен
показывать те же формулировки. Хардкод текстов в сервисах запрещён —
всё берём через nt().
"""

# Ключ → {язык: шаблон}. Шаблоны форматируются через str.format(**kwargs).
NOTIFY_TEXTS: dict[str, dict[str, str]] = {
    # === Заявки на перевозку ===
    "new_request": {
        "ru": "📩 <b>Новая заявка на ваш рейс</b>\n\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n"
              "📦 {description}\n"
              "⚖️ {weight} кг · 💰 ${price}\n"
              "👤 {sender_name} {sender_rating}",
        "en": "📩 <b>New request for your flight</b>\n\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n"
              "📦 {description}\n"
              "⚖️ {weight} kg · 💰 ${price}\n"
              "👤 {sender_name} {sender_rating}",
    },
    "request_accepted": {
        "ru": "✅ <b>Заявку приняли!</b>\n\n"
              "Перевозчик {traveler_name} {traveler_rating} везёт вашу посылку.\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n\n"
              "Договоритесь о передаче в чате.",
        "en": "✅ <b>Your request was accepted!</b>\n\n"
              "{traveler_name} {traveler_rating} will carry your parcel.\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n\n"
              "Arrange the handover in chat.",
    },
    "request_declined": {
        "ru": "❌ <b>Заявку отклонили</b>\n\n"
              "📦 {description} · {from_city} → {to_city}\n\n"
              "Посылка снова в поиске — подберём другой рейс.",
        "en": "❌ <b>Your request was declined</b>\n\n"
              "📦 {description} · {from_city} → {to_city}\n\n"
              "The parcel is searching again — we will find another flight.",
    },

    # === Матчинг ===
    "match_flight_for_parcel": {
        "ru": "🔔 <b>Нашёлся попутчик!</b>\n\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n"
              "👤 {traveler_name} {traveler_rating}\n"
              "⚖️ свободно {available_kg} кг · 💰 ${price_per_kg}/кг\n\n"
              "Ваша посылка: {description} ({weight} кг)",
        "en": "🔔 <b>A traveler was found!</b>\n\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n"
              "👤 {traveler_name} {traveler_rating}\n"
              "⚖️ {available_kg} kg free · 💰 ${price_per_kg}/kg\n\n"
              "Your parcel: {description} ({weight} kg)",
    },
    "match_parcels_for_flight": {
        "ru": "🔔 <b>Для вашего рейса есть посылки</b>\n\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n"
              "📦 Ждут отправки: {count}\n"
              "💰 Суммарно до ${total_price}\n\n"
              "Откройте приложение и примите заявки.",
        "en": "🔔 <b>There are parcels for your flight</b>\n\n"
              "✈️ {from_city} → {to_city}, {flight_date}\n"
              "📦 Waiting: {count}\n"
              "💰 Up to ${total_price} total\n\n"
              "Open the app and accept requests.",
    },

    # === Чат ===
    "new_message": {
        "ru": "💬 <b>{sender_name}</b>\n\n{text}",
        "en": "💬 <b>{sender_name}</b>\n\n{text}",
    },

    # === Статусы доставки ===
    "parcel_handed": {
        "ru": "📤 <b>Посылка передана перевозчику</b>\n\n"
              "📦 {description}\n"
              "✈️ {from_city} → {to_city}",
        "en": "📤 <b>Parcel handed to the traveler</b>\n\n"
              "📦 {description}\n"
              "✈️ {from_city} → {to_city}",
    },
    "parcel_in_transit": {
        "ru": "🛫 <b>Посылка в пути</b>\n\n"
              "📦 {description}\n"
              "✈️ {from_city} → {to_city}",
        "en": "🛫 <b>Parcel is in transit</b>\n\n"
              "📦 {description}\n"
              "✈️ {from_city} → {to_city}",
    },
    "parcel_arrived": {
        "ru": "🛬 <b>Посылка прилетела</b>\n\n"
              "📦 {description}\n"
              "Свяжитесь с перевозчиком, чтобы забрать.",
        "en": "🛬 <b>Parcel has arrived</b>\n\n"
              "📦 {description}\n"
              "Contact the traveler to pick it up.",
    },
    "parcel_delivered": {
        "ru": "🎉 <b>Посылка доставлена</b>\n\n"
              "📦 {description}\n\n"
              "Оцените перевозчика — это помогает другим.",
        "en": "🎉 <b>Parcel delivered</b>\n\n"
              "📦 {description}\n\n"
              "Rate the traveler — it helps others.",
    },
    "handover_code": {
        "ru": "🔑 <b>Код выдачи: {code}</b>\n\n"
              "Назовите его перевозчику только когда получите посылку на руки.",
        "en": "🔑 <b>Pickup code: {code}</b>\n\n"
              "Tell it to the traveler only after you receive the parcel.",
    },

    # === Кросс-постинг в группы ===
    "crosspost_flight": {
        "ru": "✈️ <b>{from_city} → {to_city}</b>, {flight_date}\n\n"
              "⚖️ Свободно <b>{available_kg} кг</b>\n"
              "💰 ${price_per_kg} за кг\n"
              "👤 {traveler_name} {traveler_rating}\n\n"
              "<i>Заявка оформляется в приложении: карточка, статусы доставки и рейтинг перевозчика.</i>",
        "en": "✈️ <b>{from_city} → {to_city}</b>, {flight_date}\n\n"
              "⚖️ <b>{available_kg} kg</b> free\n"
              "💰 ${price_per_kg} per kg\n"
              "👤 {traveler_name} {traveler_rating}\n\n"
              "<i>Requests go through the app: a card, delivery statuses and traveler rating.</i>",
    },
    "group_offer": {
        "ru": "👋 Похоже, вы везёте посылки по маршруту <b>{route}</b>.\n\n"
              "Оформите рейс в приложении — объявление само разойдётся по чатам, "
              "а заявки придут с рейтингом отправителя и статусами доставки.",
        "en": "👋 Looks like you are carrying parcels on <b>{route}</b>.\n\n"
              "Publish the flight in the app — the announcement spreads to chats by itself, "
              "and requests arrive with sender rating and delivery statuses.",
    },
    "promo_chat_added": {
        "ru": "✅ Чат подключён к рассылке рейсов.",
        "en": "✅ This chat is now receiving flight announcements.",
    },
    "promo_chat_removed": {
        "ru": "🚫 Чат отключён от рассылки рейсов.",
        "en": "🚫 This chat no longer receives flight announcements.",
    },
    "promo_admin_only": {
        "ru": "Команда доступна только администраторам сервиса.",
        "en": "This command is available to service administrators only.",
    },

    # === Поддержка ===
    "support_admin_push": {
        "ru": "🆘 <b>Обращение #{ticket_id}</b>\n\n"
              "От: {user_name} ({username})\n\n{text}",
        "en": "🆘 <b>Ticket #{ticket_id}</b>\n\n"
              "From: {user_name} ({username})\n\n{text}",
    },
    "support_user_push": {
        "ru": "🆘 <b>Ответ поддержки</b>\n\n{text}",
        "en": "🆘 <b>Support reply</b>\n\n{text}",
    },
    "support_reply_prompt": {
        "ru": "Напишите ответ пользователю {user_id}. Отправьте /cancel, чтобы выйти.",
        "en": "Write a reply to user {user_id}. Send /cancel to exit.",
    },
    "support_reply_sent": {
        "ru": "✅ Ответ отправлен.",
        "en": "✅ Reply sent.",
    },
    "support_no_ticket": {
        "ru": "У этого пользователя нет обращения.",
        "en": "This user has no open ticket.",
    },
    "support_unavailable": {
        "ru": "Поддержка пока не настроена. Попробуйте позже.",
        "en": "Support is not configured yet. Please try later.",
    },
    "support_queue_empty": {
        "ru": "Обращений без ответа нет.",
        "en": "No tickets waiting for a reply.",
    },
    "support_queue_title": {
        "ru": "🆘 <b>Обращения без ответа</b>",
        "en": "🆘 <b>Tickets waiting for a reply</b>",
    },

    # === Пополнение баланса ===
    "topup_success": {
        "ru": "⭐ <b>Баланс пополнен на {amount}</b>\n\nОстаток: {balance} ⭐",
        "en": "⭐ <b>Balance topped up by {amount}</b>\n\nBalance: {balance} ⭐",
    },

    # === Кнопки ===
    "btn_open_requests": {"ru": "📩 Открыть заявки", "en": "📩 Open requests"},
    "btn_open_app": {"ru": "🚀 Открыть приложение", "en": "🚀 Open app"},
    "btn_open_chat": {"ru": "💬 Ответить", "en": "💬 Reply"},
    "btn_open_tracking": {"ru": "📍 Отследить", "en": "📍 Track"},
    "btn_rate": {"ru": "⭐ Оценить", "en": "⭐ Rate"},
    "btn_send_with_him": {"ru": "📦 Отправить посылку", "en": "📦 Send a parcel"},
    "btn_publish_flight": {"ru": "✈️ Оформить рейс", "en": "✈️ Publish flight"},
    "btn_support_reply": {"ru": "✍️ Ответить", "en": "✍️ Reply"},
    "btn_open_support": {"ru": "🆘 Открыть поддержку", "en": "🆘 Open support"},
    "btn_open_wallet": {"ru": "⭐ Кабинет", "en": "⭐ Wallet"},
}

# Язык по умолчанию, если у пользователя не проставлен поддерживаемый
DEFAULT_LANG = "ru"


def nt(lang: str | None, key: str, **kwargs) -> str:
    """Вернуть текст уведомления на нужном языке с подстановкой значений."""
    # Неизвестный язык откатываем на русский
    variants = NOTIFY_TEXTS.get(key)
    if not variants:
        return key
    template = variants.get(lang or DEFAULT_LANG) or variants[DEFAULT_LANG]
    try:
        return template.format(**kwargs)
    except KeyError:
        # Не хватило подстановки — отдаём шаблон как есть, чтобы не терять уведомление
        return template
