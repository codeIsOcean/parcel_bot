import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class ReportReason(str, enum.Enum):
    """Причина жалобы."""
    SCAM = "scam"                 # Мошенничество
    NO_SHOW = "no_show"           # Не пришёл на передачу
    PROHIBITED = "prohibited"     # Запрещённое вложение
    RUDE = "rude"                 # Оскорбления
    OTHER = "other"               # Прочее


class ReportStatus(str, enum.Enum):
    """Состояние разбора жалобы."""
    OPEN = "open"                 # Ждёт разбора
    REVIEWED = "reviewed"         # Разобрана, мер не принято
    CONFIRMED = "confirmed"       # Подтверждена, приняты меры


class Report(TimestampMixin, Base):
    """Жалоба одного пользователя на другого."""
    __tablename__ = "reports"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Кто пожаловался
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # На кого пожаловались
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Посылка, в рамках которой возник конфликт
    parcel_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("parcels.id"), nullable=True)

    # Причина
    reason: Mapped[ReportReason] = mapped_column(
        Enum(ReportReason, name="reportreason", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        nullable=False,
    )

    # Подробности от автора жалобы
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Состояние разбора
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="reportstatus", create_constraint=True,
             values_callable=lambda enum: [e.value for e in enum]),
        default=ReportStatus.OPEN,
        nullable=False,
        index=True,
    )

    # Связи
    author = relationship("User", foreign_keys=[author_id])
    target = relationship("User", foreign_keys=[target_id])

    def __repr__(self) -> str:
        return f"<Report id={self.id} target={self.target_id} reason={self.reason}>"
