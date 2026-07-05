import enum
from sqlalchemy import ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class MatchStatus(str, enum.Enum):
    """Статусы совпадения посылка↔рейс."""
    PENDING = "pending"       # Ожидает ответа перевозчика
    ACCEPTED = "accepted"     # Принято
    DECLINED = "declined"     # Отклонено
    COUNTER = "counter"       # Контр-предложение (торг)


class Match(TimestampMixin, Base):
    """Совпадение (заявка) — связь между посылкой и рейсом."""
    __tablename__ = "matches"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Посылка
    parcel_id: Mapped[int] = mapped_column(Integer, ForeignKey("parcels.id"), nullable=False, index=True)

    # Рейс
    flight_id: Mapped[int] = mapped_column(Integer, ForeignKey("flights.id"), nullable=False, index=True)

    # Статус заявки
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="matchstatus", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=MatchStatus.PENDING,
        nullable=False,
    )

    # Связи
    parcel = relationship("Parcel", foreign_keys=[parcel_id])
    flight = relationship("Flight", back_populates="matches", foreign_keys=[flight_id])

    def __repr__(self) -> str:
        return f"<Match id={self.id} parcel={self.parcel_id} flight={self.flight_id} status={self.status}>"
