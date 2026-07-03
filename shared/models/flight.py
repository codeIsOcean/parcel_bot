import enum
from datetime import date
from sqlalchemy import BigInteger, Date, Float, ForeignKey, Integer, String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class FlightStatus(str, enum.Enum):
    """Статусы рейса."""
    ACTIVE = "active"           # Активен, принимает заявки
    FULL = "full"               # Нет свободного места
    IN_TRANSIT = "in_transit"   # В пути
    COMPLETED = "completed"     # Завершён
    CANCELLED = "cancelled"     # Отменён


class Flight(TimestampMixin, Base):
    """Модель рейса перевозчика."""
    __tablename__ = "flights"

    # Уникальный ID рейса
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Перевозчик (кто опубликовал рейс)
    traveler_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Город отправления
    from_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Город назначения
    to_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Дата вылета
    flight_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Номер рейса (опционально)
    flight_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Свободный вес (кг)
    available_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Изначальный вес (кг) — для расчёта загруженности
    total_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Цена за кг (USD)
    price_per_kg: Mapped[float] = mapped_column(Float, nullable=False)

    # Примечания
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Статус
    status: Mapped[FlightStatus] = mapped_column(
        Enum(FlightStatus, name="flightstatus", create_constraint=True),
        default=FlightStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Количество входящих заявок
    requests_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Связи
    traveler = relationship("User", back_populates="flights", foreign_keys=[traveler_id])
    matches = relationship("Match", back_populates="flight")

    def __repr__(self) -> str:
        return f"<Flight id={self.id} {self.from_city}→{self.to_city} {self.flight_date}>"
