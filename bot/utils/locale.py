"""Тексты бота. Бот — тонкая обёртка над Mini App, поэтому строк мало:
онбординг (язык, телефон), кнопка «Открыть приложение», ответы на лишнее.
"""

# Строки бота по языкам
_STRINGS = {
    "ru": {
        "choose_lang": "🌐 Выберите язык / Choose your language",
        "lang_saved": "✅ Язык: Русский",
        "ask_phone": "📱 <b>Поделитесь номером телефона</b>\n\n"
                     "Номер нужен, чтобы отправитель и перевозчик были настоящими людьми. "
                     "Другим пользователям он не показывается.\n\n"
                     "Нажмите кнопку ниже 👇",
        "btn_share_phone": "📱 Поделиться номером",
        "phone_not_yours": "⚠️ Это чужой контакт. Нажмите кнопку «Поделиться номером», чтобы отправить свой.",
        "phone_saved": "✅ Номер сохранён",
        "welcome": "👋 <b>Добро пожаловать в Parcel Bot!</b>\n\n"
                   "Отправляйте посылки с попутчиками или зарабатывайте на свободном месте в багаже.\n\n"
                   "Всё происходит в приложении — нажмите кнопку ниже.",
        "open_app_short": "Откройте приложение, чтобы продолжить 👇",
        "deeplink_ready": "Открыть в приложении 👇",
        "btn_open_app": "🚀 Открыть приложение",
        "btn_open_parcel": "📦 Открыть посылку",
        "btn_open_flight": "✈️ Открыть рейс",
        "btn_open_admin": "🛠 Открыть админ-панель",
        "help": "ℹ️ <b>Как это работает</b>\n\n"
                "Бот нужен только для регистрации и уведомлений. "
                "Посылки, рейсы, чаты, оплата и профиль — в приложении.\n\n"
                "/app — открыть приложение\n"
                "/lang — сменить язык\n"
                "/help — эта справка",
        "not_here": "Здесь только уведомления. Всё остальное — в приложении 👇",
        "no_webapp": "⚠️ Приложение временно недоступно. Попробуйте позже.",
        "admin_only": "Команда доступна только администраторам.",
    },
    "en": {
        "choose_lang": "🌐 Выберите язык / Choose your language",
        "lang_saved": "✅ Language: English",
        "ask_phone": "📱 <b>Share your phone number</b>\n\n"
                     "We need it so that senders and travelers are real people. "
                     "Other users never see it.\n\n"
                     "Tap the button below 👇",
        "btn_share_phone": "📱 Share phone number",
        "phone_not_yours": "⚠️ That is someone else's contact. Tap “Share phone number” to send yours.",
        "phone_saved": "✅ Phone number saved",
        "welcome": "👋 <b>Welcome to Parcel Bot!</b>\n\n"
                   "Send parcels with fellow travelers or earn on spare luggage space.\n\n"
                   "Everything happens in the app — tap the button below.",
        "open_app_short": "Open the app to continue 👇",
        "deeplink_ready": "Open in the app 👇",
        "btn_open_app": "🚀 Open app",
        "btn_open_parcel": "📦 Open parcel",
        "btn_open_flight": "✈️ Open flight",
        "btn_open_admin": "🛠 Open admin panel",
        "help": "ℹ️ <b>How it works</b>\n\n"
                "The bot is only for registration and notifications. "
                "Parcels, flights, chats, payments and profile live in the app.\n\n"
                "/app — open the app\n"
                "/lang — change language\n"
                "/help — this help",
        "not_here": "Only notifications live here. Everything else is in the app 👇",
        "no_webapp": "⚠️ The app is temporarily unavailable. Please try again later.",
        "admin_only": "This command is for administrators only.",
    },
}

# Поддерживаемые языки бота
SUPPORTED_LANGS = ("ru", "en")


def t(lang: str | None, key: str, **kwargs) -> str:
    """Строка бота на нужном языке с подстановкой значений."""
    # Неизвестный язык откатываем на русский
    table = _STRINGS.get(lang or "ru") or _STRINGS["ru"]
    text = table.get(key) or _STRINGS["ru"].get(key) or key
    try:
        return text.format(**kwargs) if kwargs else text
    except (KeyError, IndexError):
        return text
