"""Ответы поддержки из Telegram.

Обращение пользователя приходит администратору сообщением с кнопкой
«Ответить». Кнопка переводит администратора в режим ответа конкретному
человеку, следующее его сообщение уходит этому пользователю и ложится
в ту же переписку, которую пользователь видит в Mini App.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services import support_service
from shared.locale.notify_texts import nt
from shared.models.user import User

logger = logging.getLogger(__name__)
router = Router(name="support_admin")


class SupportReply(StatesGroup):
    """Администратор пишет ответ конкретному пользователю."""
    waiting_text = State()


def _is_admin(user_id: int) -> bool:
    """Разрешено ли отвечать от имени поддержки."""
    return user_id in settings.admin_id_list


@router.callback_query(F.data.startswith("support_reply:"))
async def on_reply_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Кнопка «Ответить» под обращением."""
    if not _is_admin(callback.from_user.id):
        await callback.answer(nt("ru", "promo_admin_only"), show_alert=True)
        return

    try:
        user_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer()
        return

    # Запоминаем адресата и ждём текст ответа
    await state.set_state(SupportReply.waiting_text)
    await state.update_data(support_user_id=user_id)

    await callback.message.answer(nt("ru", "support_reply_prompt", user_id=user_id))
    await callback.answer()


@router.message(Command("cancel"), StateFilter(SupportReply.waiting_text))
async def on_cancel_reply(message: Message, state: FSMContext) -> None:
    """Выход из режима ответа."""
    await state.clear()
    await message.answer("Отменено.")


@router.message(StateFilter(SupportReply.waiting_text), F.text)
async def on_reply_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Отправить ответ пользователю."""
    if not _is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    user_id = data.get("support_user_id")
    await state.clear()

    if not user_id:
        await message.answer(nt("ru", "support_no_ticket"))
        return

    result = await support_service.send_admin_reply(
        session, message.from_user.id, int(user_id), message.text,
    )

    if not result:
        await message.answer(nt("ru", "support_no_ticket"))
        return

    await message.answer(nt("ru", "support_reply_sent"))


@router.message(Command("support_queue"))
async def on_support_queue(message: Message, session: AsyncSession) -> None:
    """Показать обращения, которые ждут ответа."""
    if not _is_admin(message.from_user.id):
        await message.answer(nt("ru", "promo_admin_only"))
        return

    tickets = await support_service.pending_sessions(session)
    if not tickets:
        await message.answer(nt("ru", "support_queue_empty"))
        return

    lines = [nt("ru", "support_queue_title")]
    for ticket in tickets:
        user = await session.get(User, ticket.user_id)
        name = user.full_name if user else str(ticket.user_id)
        # Каждая строка — обращение с ссылкой-командой для ответа
        lines.append(f"#{ticket.id} · {name} · /reply_{ticket.user_id}")

    await message.answer("\n".join(lines))


@router.message(F.text.regexp(r"^/reply_(\d+)$"))
async def on_reply_command(message: Message, state: FSMContext) -> None:
    """Команда из очереди: перейти к ответу конкретному пользователю."""
    if not _is_admin(message.from_user.id):
        return

    user_id = int(message.text.split("_")[1])
    await state.set_state(SupportReply.waiting_text)
    await state.update_data(support_user_id=user_id)
    await message.answer(nt("ru", "support_reply_prompt", user_id=user_id))
