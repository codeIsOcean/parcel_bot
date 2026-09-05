from aiogram import F, Router

from bot.handlers.start import router as start_router
from bot.handlers.menu import router as menu_router
from bot.handlers.create_parcel import router as create_parcel_router
from bot.handlers.publish_flight import router as publish_flight_router
from bot.handlers.profile import router as profile_router
from bot.handlers.rating import router as rating_router
from bot.handlers.settings import router as settings_router
from bot.handlers.payments import router as payments_router
from bot.handlers.support_admin import router as support_admin_router
from bot.handlers.promo import router as promo_router
from bot.handlers.common import router as common_router

# Личные диалоги. Эти роутеры не должны реагировать на сообщения в группах —
# иначе catch-all начнёт отвечать на каждое чужое сообщение в чате.
_private_routers = (
    start_router, payments_router, support_admin_router,
    create_parcel_router, publish_flight_router,
    profile_router, rating_router, settings_router, menu_router, common_router,
)
for _router in _private_routers:
    _router.message.filter(F.chat.type == "private")

# Главный роутер — собирает все под-роутеры
main_router = Router(name="main")

# Порядок важен: конкретные роутеры первые, общий (catch-all) последний
main_router.include_router(start_router)
main_router.include_router(payments_router)  # Платежи — до FSM-роутеров
main_router.include_router(support_admin_router)  # Ответы поддержки
main_router.include_router(create_parcel_router)
main_router.include_router(publish_flight_router)
main_router.include_router(profile_router)
main_router.include_router(rating_router)
main_router.include_router(settings_router)
main_router.include_router(menu_router)
main_router.include_router(promo_router)  # Групповые чаты
main_router.include_router(common_router)  # Catch-all — последний
