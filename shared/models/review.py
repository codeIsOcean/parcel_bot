from sqlalchemy import BigInteger, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.base import Base, TimestampMixin


class Review(TimestampMixin, Base):
    """Отзыв — оценка после доставки."""
    __tablename__ = "reviews"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Автор отзыва
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Кому отзыв (target)
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Связанная посылка
    parcel_id: Mapped[int] = mapped_column(Integer, ForeignKey("parcels.id"), nullable=False)

    # Оценка (1-5)
    rating: Mapped[float] = mapped_column(Float, nullable=False)

    # Комментарий (опционально)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Связи
    author = relationship("User", foreign_keys=[author_id])
    target = relationship("User", back_populates="reviews_received", foreign_keys=[target_id])
    parcel = relationship("Parcel", foreign_keys=[parcel_id])

    def __repr__(self) -> str:
        return f"<Review id={self.id} author={self.author_id} target={self.target_id} rating={self.rating}>"
