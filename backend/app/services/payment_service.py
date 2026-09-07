"""Оплата: Telegram Stars и TON.

Контракт повторяет тот, что уже работает в такси-боте, чтобы не изобретать
второй раз: счёт создаёт сервер, payload формируется сервером и содержит
пользователя и сумму, сумма разрешена только из фиксированных пакетов.
Истина о платеже приходит не от фронта, а от Telegram в бота
(pre_checkout и successful_payment) либо из блокчейна для TON.

Зачисление идемпотентно: для звёзд ключом служит идентификатор списания
Telegram, для TON — хеш транзакции.
"""

import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.services import balance_service
from shared.models.payment import Payment, PaymentKind, PaymentMethod, PaymentStatus
from shared.notify import call_api

logger = logging.getLogger(__name__)

# Валюта Telegram Stars
CURRENCY_XTR = "XTR"

# Префиксы payload. По ним бот отличает свои счета от чужих.
PAYLOAD_TOPUP = "topup"

# Запасной курс TON к доллару, если внешний источник недоступен
_TON_FALLBACK_RATE = 3.0

# Кеш курса TON
_ton_rate: float | None = None
_ton_rate_at: float = 0.0
_TON_RATE_TTL = 300


@dataclass
class InvoiceResult:
    """Итог создания счёта."""
    ok: bool
    error: str | None = None
    payment_id: int | None = None
    # Ссылка на счёт для Mini App
    invoice_link: str | None = None
    # Реквизиты перевода TON
    wallet_address: str | None = None
    amount_ton: float | None = None
    payment_code: str | None = None
    expires_at: datetime | None = None
    deep_link: str | None = None


def _now() -> datetime:
    """Текущее время в UTC."""
    return datetime.now(timezone.utc)


def is_allowed_amount(amount_stars: int) -> bool:
    """Разрешена ли такая сумма пополнения."""
    # Произвольные суммы запрещены: иначе payload можно подобрать под что угодно
    return amount_stars in settings.topup_packages


def stars_to_usd(amount_stars: int) -> float:
    """Пересчёт звёзд в доллары по фиксированному курсу конфига."""
    return round(amount_stars * settings.star_usd_rate, 2)


async def get_ton_usd_rate() -> float:
    """Курс TON к доллару с кешем на несколько минут."""
    global _ton_rate, _ton_rate_at

    now = time.time()
    if _ton_rate and now - _ton_rate_at < _TON_RATE_TTL:
        return _ton_rate

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "the-open-network", "vs_currencies": "usd"},
            )
        rate = float(response.json()["the-open-network"]["usd"])
        if rate > 0:
            _ton_rate, _ton_rate_at = rate, now
            return rate
    except Exception as e:
        logger.warning("[TON] Курс недоступен, берём запасной: %s", e)

    return _ton_rate or _TON_FALLBACK_RATE


# === Telegram Stars ===

async def create_stars_topup_link(
    session: AsyncSession, user_id: int, amount_stars: int,
) -> InvoiceResult:
    """Создать ссылку на счёт пополнения баланса звёздами."""
    if not is_allowed_amount(amount_stars):
        return InvoiceResult(ok=False, error="bad_amount")

    payment = Payment(
        user_id=user_id,
        amount=stars_to_usd(amount_stars),
        amount_stars=amount_stars,
        method=PaymentMethod.STARS,
        status=PaymentStatus.PENDING,
        kind=PaymentKind.TOPUP,
        description=f"Пополнение баланса на {amount_stars} звёзд",
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    # payload формирует сервер: пользователь не может подменить сумму
    payload = f"{PAYLOAD_TOPUP}:{user_id}:{amount_stars}"

    link = await call_api("createInvoiceLink", {
        "title": f"Пополнение на {amount_stars} ⭐",
        "description": "Баланс тратится на публикацию рейсов",
        "payload": payload,
        "currency": CURRENCY_XTR,
        "prices": [{"label": f"{amount_stars} ⭐", "amount": amount_stars}],
    })

    if not link:
        payment.status = PaymentStatus.FAILED
        await session.commit()
        return InvoiceResult(ok=False, error="invoice_failed", payment_id=payment.id)

    logger.info("[PAYMENT] Счёт на звёзды: user=%s, %s ⭐", user_id, amount_stars)
    return InvoiceResult(ok=True, payment_id=payment.id, invoice_link=link)


def parse_topup_payload(payload: str) -> tuple[int, int] | None:
    """Разобрать payload пополнения в пару из пользователя и суммы."""
    try:
        prefix, user_raw, amount_raw = payload.split(":")
    except ValueError:
        return None

    if prefix != PAYLOAD_TOPUP:
        return None

    try:
        return int(user_raw), int(amount_raw)
    except ValueError:
        return None


def validate_topup_payload(payload: str) -> tuple[bool, str]:
    """Проверить payload перед подтверждением платежа."""
    parsed = parse_topup_payload(payload)
    if not parsed:
        return False, "Некорректный платёж"

    _, amount_stars = parsed
    # Сумма обязана быть из разрешённых пакетов
    if not is_allowed_amount(amount_stars):
        return False, "Недопустимая сумма пополнения"

    return True, ""


async def complete_stars_topup(
    session: AsyncSession, payload: str, telegram_charge_id: str,
) -> balance_service.BalanceResult:
    """Зачислить пополнение после успешной оплаты звёздами."""
    parsed = parse_topup_payload(payload)
    if not parsed:
        return balance_service.BalanceResult(ok=False, balance=0, reason="bad_payload")

    user_id, amount_stars = parsed
    if not is_allowed_amount(amount_stars):
        return balance_service.BalanceResult(ok=False, balance=0, reason="bad_amount")

    # Ключ идемпотентности — идентификатор списания от Telegram
    result = await balance_service.top_up(
        session, user_id, amount_stars,
        external_ref=f"stars:{telegram_charge_id}",
        note=f"Пополнение Telegram Stars на {amount_stars} ⭐",
    )

    # Отмечаем платёж завершённым, если он был заведён при создании счёта
    payment = (await session.execute(
        select(Payment)
        .where(
            Payment.user_id == user_id,
            Payment.kind == PaymentKind.TOPUP,
            Payment.method == PaymentMethod.STARS,
            Payment.status == PaymentStatus.PENDING,
            Payment.amount_stars == amount_stars,
        )
        .order_by(Payment.id.desc())
        .limit(1)
    )).scalar_one_or_none()

    if payment:
        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = f"stars:{telegram_charge_id}"
        payment.completed_at = _now()
        await session.commit()

    logger.info("[PAYMENT] Звёзды зачислены: user=%s, %s ⭐, повтор=%s",
                user_id, amount_stars, result.reason == "duplicate")
    return result


# === TON ===

async def create_ton_topup(
    session: AsyncSession, user_id: int, amount_stars: int,
) -> InvoiceResult:
    """Создать счёт на пополнение баланса переводом в TON."""
    if not is_allowed_amount(amount_stars):
        return InvoiceResult(ok=False, error="bad_amount")

    wallet = settings.ton_wallet_address
    if not wallet:
        return InvoiceResult(ok=False, error="ton_not_configured")

    amount_usd = stars_to_usd(amount_stars)
    rate = await get_ton_usd_rate()
    # Округляем вверх до сотых, чтобы недоплата не блокировала зачисление
    amount_ton = round(amount_usd / rate + 0.005, 2)

    payment = Payment(
        user_id=user_id,
        amount=amount_usd,
        amount_stars=amount_stars,
        amount_ton=amount_ton,
        method=PaymentMethod.TON,
        status=PaymentStatus.PENDING,
        kind=PaymentKind.TOPUP,
        description=f"Пополнение баланса на {amount_stars} звёзд через TON",
        expires_at=_now() + timedelta(seconds=settings.ton_payment_timeout_seconds),
    )
    session.add(payment)
    await session.flush()

    # Код случайный: по последовательному можно было бы оплатить за чужой счёт
    payment.payment_code = f"PB{payment.id}X{secrets.token_hex(3).upper()}"
    await session.commit()
    await session.refresh(payment)

    logger.info("[TON] Счёт: user=%s, %s TON, код=%s", user_id, amount_ton, payment.payment_code)
    return InvoiceResult(
        ok=True,
        payment_id=payment.id,
        wallet_address=wallet,
        amount_ton=amount_ton,
        payment_code=payment.payment_code,
        expires_at=payment.expires_at,
        deep_link=f"ton://transfer/{wallet}?amount={int(amount_ton * 1_000_000_000)}"
                  f"&text={payment.payment_code}",
    )


# Кэш последнего ответа toncenter: ручная «проверка» из кабинета не должна
# исчерпывать квоту API
_ton_tx_cache: list | None = None
_ton_tx_cached_at: float = 0.0
_TON_TX_TTL = 15.0


async def fetch_ton_transactions() -> list | None:
    """Последние поступления на кошелёк сервиса."""
    global _ton_tx_cache, _ton_tx_cached_at
    wallet = settings.ton_wallet_address
    if not wallet:
        return None

    if _ton_tx_cache is not None and time.time() - _ton_tx_cached_at < _TON_TX_TTL:
        return _ton_tx_cache

    headers = {"X-API-Key": settings.ton_api_key} if settings.ton_api_key else {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{settings.ton_api_url.rstrip('/')}/getTransactions",
                params={"address": wallet, "limit": 50},
                headers=headers,
            )
        data = response.json()
    except Exception as e:
        logger.warning("[TON] Не удалось получить транзакции: %s", e)
        return None

    if not data.get("ok"):
        logger.warning("[TON] Ответ с ошибкой: %s", str(data)[:200])
        return None

    _ton_tx_cache = data.get("result", [])
    _ton_tx_cached_at = time.time()
    return _ton_tx_cache


def _extract_comment(transaction: dict) -> str:
    """Комментарий входящего перевода — в нём лежит код платежа."""
    in_msg = transaction.get("in_msg") or {}
    # Разные версии API кладут текст в разные поля
    message = in_msg.get("message")
    if message:
        return str(message)
    decoded = (in_msg.get("msg_data") or {}).get("text")
    return str(decoded or "")


def _extract_amount_ton(transaction: dict) -> float:
    """Сумма входящего перевода в TON."""
    in_msg = transaction.get("in_msg") or {}
    try:
        return int(in_msg.get("value", 0)) / 1_000_000_000
    except (TypeError, ValueError):
        return 0.0


async def check_ton_payments(session: AsyncSession) -> int:
    """Найти оплаченные TON-счета и зачислить баланс.

    Возвращает количество зачисленных платежей.
    """
    pending = list((await session.execute(
        select(Payment).where(
            Payment.method == PaymentMethod.TON,
            Payment.status == PaymentStatus.PENDING,
            Payment.kind == PaymentKind.TOPUP,
        )
    )).scalars().all())

    if not pending:
        return 0

    # Просроченные счета закрываем, не дожидаясь перевода
    now = _now()
    still_waiting = []
    for payment in pending:
        if payment.expires_at and payment.expires_at < now:
            payment.status = PaymentStatus.FAILED
        else:
            still_waiting.append(payment)
    if len(still_waiting) != len(pending):
        await session.commit()

    if not still_waiting:
        return 0

    transactions = await fetch_ton_transactions()
    if not transactions:
        return 0

    # Собираем поступления по коду в комментарии
    by_code: dict[str, dict] = {}
    for transaction in transactions:
        comment = _extract_comment(transaction).strip().upper()
        if comment:
            by_code.setdefault(comment, transaction)

    credited = 0
    for payment in still_waiting:
        transaction = by_code.get((payment.payment_code or "").upper())
        if not transaction:
            continue

        # Недоплату не засчитываем: допускаем только небольшую погрешность округления
        paid_ton = _extract_amount_ton(transaction)
        if paid_ton + 0.005 < (payment.amount_ton or 0):
            logger.warning(
                "[TON] Недоплата по коду %s: пришло %s, ожидалось %s",
                payment.payment_code, paid_ton, payment.amount_ton,
            )
            continue

        tx_hash = transaction.get("transaction_id", {}).get("hash") or payment.payment_code

        result = await balance_service.top_up(
            session, payment.user_id, payment.amount_stars or 0,
            external_ref=f"ton:{tx_hash}",
            note=f"Пополнение TON на {payment.amount_stars} ⭐",
        )
        if not result.ok:
            continue

        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = f"ton:{tx_hash}"
        payment.completed_at = now
        await session.commit()
        credited += 1

        logger.info("[TON] Зачислено: user=%s, %s ⭐", payment.user_id, payment.amount_stars)

    return credited
