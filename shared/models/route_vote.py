from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from shared.models.base import Base, TimestampMixin


class RouteVote(TimestampMixin, Base):
    """Голосование за новый маршрут."""
    __tablename__ = "route_votes"
    # Один пользователь — один голос за маршрут
    __table_args__ = (
        UniqueConstraint("user_id", "route_name", name="uq_user_route_vote"),
    )

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Кто проголосовал
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    # Название предложенного маршрута (например "Dubai → London")
    route_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Количество голосов (денормализовано для быстрого доступа)
    # Обновляется триггером или вручную
    votes_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    def __repr__(self) -> str:
        return f"<RouteVote id={self.id} route={self.route_name}>"
