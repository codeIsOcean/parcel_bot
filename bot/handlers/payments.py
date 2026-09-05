"""Приём платежей Telegram Stars.

Счёт создаёт бэкенд, а истина о платеже приходит сюда: Telegram сначала
спрашивает подтверждение (pre_checkout), затем присылает факт списания
(successful_payment). Зачисление идемпотентно по идентификатору списания,
поэтому повторная доставка события баланс не удвоит.
"""

import logging

from aiogram import Bot, F, Router
from aiogram.types import Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services import payment_service
from shared.locale.notify_texts import nt
from shared.models.user import User

logger = logging.getLogger(__name__)
router = Router(name="payments")


@router.pre_checkout_query(F.invoice_payload.startswith(f"{payment_service.PAYLOAD_TOPUP}:"))
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    """Подтвердить или отклонить платёж до списания."""
    ok, error = payment_service.validate_topup_payload(query.invoice_payload)

    # Telegram ждёт ответ в течение нескольких секунд, поэтому проверка синхронная
    if ok:
        await query.answer(ok=True)
    else:
        logger.warning("[PAYMENT] Отклонён pre_checkout: %s", error)
        await query.answer(ok=False, error_message=error)


@router.pre_checkout_query()
async def on_unknown_pre_checkout(query: PreCheckoutQuery) -> None:
    """Чужой или устаревший счёт подтверждать нельзя."""
    logger.warning("[PAYMENT] Неизвестный payload: %s", query.invoice_payload)
    await query.answer(ok=False, error_message="Неизвестный платёж")


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Зачислить пополнение после успешной оплаты."""
    payment = message.successful_payment
    payload = payment.invoice_payload

    if not payload.startswith(f"{payment_service.PAYLOAD_TOPUP}:"):
        logger.warning("[PAYMENT] Платёж с чужим payload: %s", payload)
        return

    result = await payment_service.complete_stars_topup(
        session, payload, payment.telegram_payment_charge_id,
    )

    if not result.ok:
        logger.error("[PAYMENT] Не удалось зачислить: %s", result.reason)
        return

    # Язык берём из профиля, чтобы подтверждение пришло на нужном
    user = await session.get(User, message.from_user.id)
    lang = user.lang if user else "ru"

    await message.answer(nt(
        lang, "topup_success",
        amount=f"{payment.total_amount} ⭐",
        balance=result.balance,
    ))
