from aiogram import F, Router

from bot.handlers.start import router as start_router
from bot.handlers.payments import router as payments_router
from bot.handlers.support_admin import router as support_admin_router
from bot.handlers.promo import router as promo_router
from bot.handlers.groups import router as groups_router
from bot.handlers.common import router as common_router

# Личные диалоги. Эти роутеры не должны реагировать на сообщения в группах —
# иначе catch-all начнёт отвечать на каждое чужое сообщение в чате.
_private_routers = (start_router, payments_router, support_admin_router, common_router)
for _router in _private_routers:
    _router.message.filter(F.chat.type == "private")

# Главный роутер — собирает все под-роутеры.
# Бот тонкий: вход и онбординг, платежи, ответы поддержки, группы, запасной.
main_router = Router(name="main")
main_router.include_router(start_router)
main_router.include_router(payments_router)  # Платежи — до остальных
main_router.include_router(support_admin_router)  # Ответы поддержки из Telegram
main_router.include_router(groups_router)  # Членство бота в группах
main_router.include_router(promo_router)  # Команды и объявления в группах
main_router.include_router(common_router)  # Catch-all — последний
