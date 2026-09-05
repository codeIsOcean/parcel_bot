import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class BalanceTxnKind(str, enum.Enum):
    """Тип движения по балансу."""
    TOPUP = "topup"        # Пополнение звёздами или TON
    CHARGE = "charge"      # Списание за публикацию рейса
    REFUND = "refund"      # Возврат


class BalanceTransaction(TimestampMixin, Base):
    """Движение по балансу пользователя.

    Балансовый журнал: каждая операция записывается отдельной строкой,
    а поле balance_after хранит остаток после неё. По журналу всегда можно
    сверить итоговый баланс и разобрать спор.

    Идемпотентность держится на external_ref: для звёзд туда пишется
    идентификатор списания Telegram, для TON — хеш транзакции. Повторная
    доставка того же события не зачислит деньги дважды.
    """
    __tablename__ = "balance_transactions"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Владелец баланса
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Тип операции
    kind: Mapped[BalanceTxnKind] = mapped_column(
        Enum(BalanceTxnKind, name="balancetxnkind", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        nullable=False,
        index=True,
    )

    # Сумма в звёздах, всегда положительная. Знак задаёт тип операции.
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)

    # Остаток после операции
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    # Внешний идентификатор события, по которому ловим дубли
    external_ref: Mapped[str | None] = mapped_column(
        String(200), nullable=True, unique=True, index=True,
    )

    # Человекочитаемое пояснение
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<BalanceTransaction id={self.id} user={self.user_id} {self.kind} {self.amount_stars}>"
