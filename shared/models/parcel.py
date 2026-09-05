import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class ParcelStatus(str, enum.Enum):
    """Статусы посылки."""
    PENDING = "pending"         # Создана, ищет перевозчика
    ACCEPTED = "accepted"       # Перевозчик принял
    HANDED = "handed"           # Передана перевозчику
    IN_TRANSIT = "in_transit"   # В пути
    DELIVERED = "delivered"     # Доставлена
    CANCELLED = "cancelled"    # Отменена


class ParcelSize(str, enum.Enum):
    """Размер посылки."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Parcel(TimestampMixin, Base):
    """Модель посылки — заявка на отправку."""
    __tablename__ = "parcels"

    # Уникальный ID посылки
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Отправитель (кто создал заявку)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Перевозчик (кто принял заявку) — может быть null до принятия
    traveler_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

    # Город отправления
    from_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Город назначения
    to_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Описание содержимого
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Вес в кг
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    # Размер
    size: Mapped[ParcelSize] = mapped_column(
        Enum(ParcelSize, name="parcelsize", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=ParcelSize.MEDIUM,
        nullable=False,
    )

    # Предложенная цена (USD)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # Принятая цена (после торга, может отличаться)
    accepted_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Фото посылки (file_id из Telegram, через запятую если несколько)
    photo_file_ids: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Текущий статус
    status: Mapped[ParcelStatus] = mapped_column(
        Enum(ParcelStatus, name="parcelstatus", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=ParcelStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Жизненный цикл доставки ===

    # Код выдачи. Выдаётся отправителю при передаче посылки перевозчику,
    # перевозчик вводит его при выдаче — это подтверждение доставки.
    handover_code: Mapped[str | None] = mapped_column(String(6), nullable=True)

    # Когда посылка передана перевозчику
    handed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Когда перевозчик вылетел
    in_transit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Когда перевозчик прилетел в город назначения
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Когда посылка выдана получателю
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Фото при передаче перевозчику
    handover_photo_file_ids: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Фото при выдаче получателю
    delivery_photo_file_ids: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи
    sender = relationship("User", back_populates="parcels", foreign_keys=[sender_id])
    traveler = relationship("User", foreign_keys=[traveler_id])

    def __repr__(self) -> str:
        return f"<Parcel id={self.id} {self.from_city}→{self.to_city} status={self.status}>"
