import enum
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class SubscriptionPlan(str, enum.Enum):
    """Планы подписки."""
    MONTHLY = "monthly"       # 1 месяц
    QUARTERLY = "quarterly"   # 3 месяца
    YEARLY = "yearly"         # 12 месяцев
    TRIAL = "trial"           # Пробный период


class Subscription(TimestampMixin, Base):
    """Подписка перевозчика."""
    __tablename__ = "subscriptions"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Пользователь
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # План подписки
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, name="subscriptionplan", create_constraint=True),
        nullable=False,
    )

    # Активна ли подписка
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Дата начала
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Дата окончания
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Цена (USD)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # Метод оплаты (stars / ton)
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Напоминание отправлено (за 3 дня до окончания)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связи
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user={self.user_id} plan={self.plan} active={self.is_active}>"
