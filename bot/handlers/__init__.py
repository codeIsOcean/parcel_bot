from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.menu import router as menu_router
from bot.handlers.create_parcel import router as create_parcel_router
from bot.handlers.publish_flight import router as publish_flight_router
from bot.handlers.profile import router as profile_router
from bot.handlers.rating import router as rating_router
from bot.handlers.settings import router as settings_router
from bot.handlers.common import router as common_router

# Главный роутер — собирает все под-роутеры
main_router = Router(name="main")

# Порядок важен: конкретные роутеры первые, общий (catch-all) последний
main_router.include_router(start_router)
main_router.include_router(create_parcel_router)
main_router.include_router(publish_flight_router)
main_router.include_router(profile_router)
main_router.include_router(rating_router)
main_router.include_router(settings_router)
main_router.include_router(menu_router)
main_router.include_router(common_router)  # Catch-all — последний
