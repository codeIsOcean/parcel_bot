import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models.subscription import Subscription, SubscriptionPlan
from shared.models.payment import Payment, PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)


async def get_active_subscription(
    session: AsyncSession,
    user_id: int,
) -> Subscription | None:
    """Получить активную подписку пользователя."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.expires_at > now)
        .order_by(Subscription.expires_at.desc())
    )
    return result.scalar_one_or_none()


async def create_subscription(
    session: AsyncSession,
    user_id: int,
    plan: str,
    payment_method: str,
    price: float,
    transaction_id: str | None = None,
) -> Subscription:
    """Создать подписку после подтверждения оплаты."""
    logger.info("[SUBSCRIPTION] Создание: user=%s, plan=%s, method=%s", user_id, plan, payment_method)

    # Проверяем что нет активной подписки
    existing = await get_active_subscription(session, user_id)
    if existing:
        raise ValueError("User already has an active subscription")

    plan_enum = SubscriptionPlan(plan)

    # Предупреждаем об отсутствии transaction_id для платных подписок
    if plan_enum != SubscriptionPlan.TRIAL and not transaction_id:
        logger.warning(
            "[SUBSCRIPTION] Платная подписка без transaction_id: user=%s, plan=%s",
            user_id, plan,
        )

    # Определяем длительность
    durations = {
        SubscriptionPlan.MONTHLY: timedelta(days=30),
        SubscriptionPlan.QUARTERLY: timedelta(days=90),
        SubscriptionPlan.YEARLY: timedelta(days=365),
        SubscriptionPlan.TRIAL: timedelta(days=7),
    }
    duration = durations.get(plan_enum, timedelta(days=30))

    now = datetime.now(timezone.utc)

    # Создаём подписку
    subscription = Subscription(
        user_id=user_id,
        plan=plan_enum,
        starts_at=now,
        expires_at=now + duration,
        price=price,
        payment_method=payment_method,
    )
    session.add(subscription)

    # Flush чтобы получить subscription.id до создания платежа
    await session.flush()

    # Создаём запись о платеже (статус PENDING до верификации)
    payment_status = PaymentStatus.COMPLETED if plan_enum == SubscriptionPlan.TRIAL else PaymentStatus.PENDING
    payment = Payment(
        user_id=user_id,
        subscription_id=subscription.id,
        amount=price,
        method=PaymentMethod(payment_method),
        status=payment_status,
        transaction_id=transaction_id,
        description=f"Subscription: {plan}",
    )
    session.add(payment)

    await session.commit()
    await session.refresh(subscription)

    logger.info("[SUBSCRIPTION] Создана: sub_id=%s, expires=%s", subscription.id, subscription.expires_at)
    return subscription


async def get_subscription_history(
    session: AsyncSession,
    user_id: int,
) -> list[Subscription]:
    """Получить историю подписок пользователя."""
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    )
    return list(result.scalars().all())
