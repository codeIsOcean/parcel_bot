import logging

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from backend.app.services import user_service
from bot.states.rating_states import RatingStates
from bot.utils.locale import t
from bot.utils.screen_manager import ScreenManager
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.review import Review

logger = logging.getLogger(__name__)
router = Router(name="rating")


def _get_stars_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора оценки (1-5 звёзд)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="rate:1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rate:2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rate:3"),
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rate:4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rate:5"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])


def _get_comment_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Клавиатура для шага комментария (Пропустить / Отмена)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "skip"), callback_data="rate_comment:skip"),
        ],
        [
            InlineKeyboardButton(text=t(lang, "cancel"), callback_data="cancel"),
        ],
    ])


# === Вход в FSM оценки ===

@router.callback_query(F.data.startswith("start_rate:"))
async def start_rating(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Начало FSM — оценка доставки. Формат: start_rate:{parcel_id}:{target_id}"""
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Invalid data", show_alert=True)
        return

    parcel_id = int(parts[1])
    target_id = int(parts[2])

    user, _ = await user_service.get_or_create_user(
        session, telegram_id=callback.from_user.id, first_name=callback.from_user.first_name,
    )
    lang = user.lang
    screen = ScreenManager(bot)

    # Проверяем что посылка существует и доставлена
    parcel = await session.get(Parcel, parcel_id)
    if not parcel:
        await callback.answer("Parcel not found", show_alert=True)
        return
    if parcel.status != ParcelStatus.DELIVERED:
        await callback.answer("Parcel must be delivered first", show_alert=True)
        return

    # Проверяем что пользователь — участник доставки
    if user.id not in (parcel.sender_id, parcel.traveler_id):
        await callback.answer("You are not a participant", show_alert=True)
        return

    # Проверяем дублирование отзыва
    existing = await session.execute(
        select(Review).where(
            Review.author_id == user.id,
            Review.parcel_id == parcel_id,
        )
    )
    if existing.scalar_one_or_none():
        await callback.answer("You already reviewed this delivery", show_alert=True)
        return

    # Сохраняем данные для оценки
    await state.set_state(RatingStates.rating)
    await state.update_data(lang=lang, parcel_id=parcel_id, target_id=target_id)

    await screen.show(
        callback.from_user.id,
        t(lang, "choose_rating"),
        slot="inline",
        reply_markup=_get_stars_keyboard(lang),
    )
    await callback.answer()


# === Шаг 0: Выбор звёзд ===

@router.callback_query(RatingStates.rating, F.data.startswith("rate:"))
async def on_rating_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Выбрана оценка (1-5 звёзд)."""
    rating = int(callback.data.split(":")[1])
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    # Сохраняем оценку
    await state.update_data(rating=rating)
    await state.set_state(RatingStates.comment)

    # Запрашиваем комментарий
    await screen.edit(
        callback.from_user.id,
        t(lang, "enter_review_comment"),
        slot="inline",
        reply_markup=_get_comment_keyboard(lang),
    )
    await callback.answer()


# === Шаг 1: Комментарий (текст или пропуск) ===

@router.callback_query(RatingStates.comment, F.data == "rate_comment:skip")
async def on_comment_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    """Пропуск комментария — сохраняем отзыв."""
    await _save_review(callback.from_user.id, state, session, bot, comment=None)
    await callback.answer()


@router.message(RatingStates.comment, F.text)
async def on_comment_text(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Получен текст комментария — сохраняем отзыв."""
    comment = message.text.strip()
    if len(comment) > 1000:
        comment = comment[:1000]
    await _save_review(message.from_user.id, state, session, bot, comment=comment)


# === Сохранение отзыва ===

async def _save_review(
    chat_id: int,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    comment: str | None,
):
    """Сохранить отзыв в БД и пересчитать рейтинг."""
    data = await state.get_data()
    lang = data.get("lang", "ru")
    screen = ScreenManager(bot)

    parcel_id = data["parcel_id"]
    target_id = data["target_id"]
    rating = data["rating"]

    try:
        # Создаём отзыв
        review = Review(
            author_id=chat_id,
            target_id=target_id,
            parcel_id=parcel_id,
            rating=float(rating),
            comment=comment,
        )
        session.add(review)
        await session.commit()

        # Пересчитываем рейтинг получателя
        await user_service.recalculate_rating(session, target_id)

        logger.info(
            "[RATING] Отзыв сохранён: author=%s, target=%s, parcel=%s, rating=%s",
            chat_id, target_id, parcel_id, rating,
        )

        await state.clear()
        await screen.edit(chat_id, t(lang, "review_saved"), slot="inline")

    except Exception as e:
        logger.error("[RATING] Ошибка сохранения отзыва: %s", e)
        await state.clear()
        await screen.show(chat_id, "❌ Error", slot="temp")
