import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class PaymentStatus(str, enum.Enum):
    """Статусы платежа."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    """Методы оплаты."""
    STARS = "stars"
    TON = "ton"
    BALANCE = "balance"


class PaymentKind(str, enum.Enum):
    """За что платёж."""
    TOPUP = "topup"      # Пополнение баланса
    POST = "post"        # Оплата публикации рейса
    SUBSCRIPTION = "subscription"  # Подписка (второй тариф)


class Payment(TimestampMixin, Base):
    """Платёж — оплата подписки."""
    __tablename__ = "payments"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Пользователь
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Связанная подписка
    subscription_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    # Сумма (USD)
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Метод оплаты
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="paymentmethod", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        nullable=False,
    )

    # Статус
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="paymentstatus", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=PaymentStatus.PENDING,
        nullable=False,
    )

    # ID транзакции (Telegram payment_charge_id или TON tx hash).
    # Уникален: защищает от повторного зачисления одного и того же платежа.
    transaction_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True, index=True,
    )

    # За что платёж
    kind: Mapped[PaymentKind] = mapped_column(
        Enum(PaymentKind, name="paymentkind", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=PaymentKind.TOPUP,
        nullable=False,
        index=True,
    )

    # Сумма в звёздах (для Stars и для пополнения через TON)
    amount_stars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Сумма в TON
    amount_ton: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Код платежа для TON: пользователь указывает его в комментарии перевода.
    # Случайный, чтобы нельзя было подобрать чужой и «оплатить за друга».
    payment_code: Mapped[str | None] = mapped_column(
        String(40), nullable=True, unique=True, index=True,
    )

    # До какого момента ждём поступления TON
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Когда платёж завершён
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Описание
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<Payment id={self.id} user={self.user_id} amount={self.amount} status={self.status}>"
