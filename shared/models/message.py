from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class RelayMessage(TimestampMixin, Base):
    """Сообщение relay-чата между отправителем и перевозчиком."""
    __tablename__ = "relay_messages"

    # Уникальный ID сообщения
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ID чата (группируем сообщения по чату)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Отправитель сообщения
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    # Получатель сообщения
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    # ID связанной посылки
    parcel_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("parcels.id"), nullable=True)

    # Текст сообщения
    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Тип сообщения (text, offer, system)
    message_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False)

    # Предложение цены (если message_type == "offer")
    offer_price: Mapped[float | None] = mapped_column(nullable=True)

    # Прочитано получателем
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связи
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

    def __repr__(self) -> str:
        return f"<RelayMessage id={self.id} chat={self.chat_id} from={self.sender_id}>"
