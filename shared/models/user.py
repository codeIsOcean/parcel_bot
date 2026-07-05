import enum
from sqlalchemy import BigInteger, Boolean, Float, Integer, String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """Роли пользователя."""
    SENDER = "sender"
    TRAVELER = "traveler"
    BOTH = "both"


class User(TimestampMixin, Base):
    """Модель пользователя — отправитель или перевозчик."""
    __tablename__ = "users"

    # Telegram user ID (уникальный идентификатор)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Имя пользователя (из Telegram или заданное)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Telegram username (@username)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Телефон (опционально, для верификации)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Город проживания
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Текущая роль
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=UserRole.SENDER,
        nullable=False,
    )

    # Рейтинг (средний, от 0 до 5)
    rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Количество завершённых доставок
    deliveries_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Количество полученных отзывов
    reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Верификация паспорта
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Telegram Premium
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Бот заблокирован пользователем
    bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Язык интерфейса (ru / en / kz)
    lang: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)

    # Уведомления включены
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # URL аватара (file_id из Telegram)
    avatar_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Биография / описание
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи
    parcels = relationship("Parcel", back_populates="sender", foreign_keys="Parcel.sender_id")
    flights = relationship("Flight", back_populates="traveler", foreign_keys="Flight.traveler_id")
    reviews_received = relationship("Review", back_populates="target", foreign_keys="Review.target_id")

    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.full_name}>"
