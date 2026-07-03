import logging

from aiogram import Bot, Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import user_service
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager

logger = logging.getLogger(__name__)
router = Router(name="profile")


@router.message(F.text.contains("Профиль") | F.text.contains("Profile"), StateFilter(None))
async def on_profile(message: Message, session: AsyncSession, bot: Bot):
    """Кнопка 'Профиль' — показать профиль пользователя."""
    user, _ = await user_service.get_or_create_user(
        session, telegram_id=message.from_user.id, first_name=message.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Формируем текст профиля
    verified_text = t(lang, "verified") if user.is_verified else t(lang, "not_verified")
    rating_str = f"{user.rating:.1f}" if user.rating else "—"

    text = t(
        lang, "profile_text",
        name=user.full_name,
        rating=rating_str,
        deliveries=user.deliveries_count,
        reviews=user.reviews_count,
        verified_text=verified_text,
    )

    await screen.show(message.from_user.id, text, slot="inline")
