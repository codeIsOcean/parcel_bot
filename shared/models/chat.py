from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class ChatSession(TimestampMixin, Base):
    """Переписка между отправителем и перевозчиком по одной посылке.

    Раньше чат существовал только как поток сообщений: получатель вычислялся
    из уже существующей переписки, поэтому начать новый чат было невозможно.
    Сессия задаёт участников явно и создаётся в момент отклика на рейс.
    """
    __tablename__ = "chat_sessions"

    # Уникальный ID. Он же используется как chat_id в сообщениях.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Посылка, вокруг которой идёт переписка. Один чат на посылку.
    parcel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("parcels.id"), nullable=False, unique=True, index=True,
    )

    # Отправитель посылки
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Перевозчик
    traveler_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Активна ли переписка. Закрывается после доставки.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Сколько сообщений отправлено
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Когда закрыта
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def other_side(self, user_id: int) -> int | None:
        """Второй участник переписки."""
        # Возвращаем None, если пользователь к этому чату не относится
        if user_id == self.sender_id:
            return self.traveler_id
        if user_id == self.traveler_id:
            return self.sender_id
        return None

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} parcel={self.parcel_id}>"


class SupportSession(TimestampMixin, Base):
    """Обращение пользователя в поддержку.

    У одного пользователя одновременно живёт одно активное обращение —
    так переписка не рассыпается на десяток веток.
    """
    __tablename__ = "support_sessions"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Кто обратился
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Открыто ли обращение
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Ждёт ли ответа администратора
    is_pending: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Сколько сообщений в переписке
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Когда закрыто
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связи
    messages = relationship(
        "SupportMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SupportMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<SupportSession id={self.id} user={self.user_id} active={self.is_active}>"


class SupportMessage(TimestampMixin, Base):
    """Сообщение в переписке с поддержкой."""
    __tablename__ = "support_messages"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Обращение
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("support_sessions.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    # Кто написал
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Роль отправителя: user или admin
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Текст
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Прочитано ли получателем
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связи
    session = relationship("SupportSession", back_populates="messages")

    __table_args__ = (
        Index("ix_support_messages_session_created", "session_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SupportMessage id={self.id} role={self.sender_role}>"
