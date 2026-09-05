from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, TimestampMixin


class PromoChat(Base, TimestampMixin):
    """Телеграм-чат, куда бот кросс-постит опубликованные рейсы.

    Решает холодный старт: перевозчик заполняет карточку один раз,
    а объявление само уходит в профильные группы со ссылкой на неё.
    """
    __tablename__ = "promo_chats"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ID чата в Telegram (у групп он отрицательный)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)

    # Название чата — чтобы владелец понимал, куда идёт рассылка
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Кто добавил чат в рассылку
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Фильтр по городам через запятую. Пусто — шлём все рейсы.
    # Пример: "Dubai,Almaty" — только рейсы, где один из городов совпал.
    cities: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Включён ли чат в рассылку
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Сколько объявлений успешно ушло
    posts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def matches_route(self, from_city: str, to_city: str) -> bool:
        """Подходит ли рейс под фильтр городов этого чата."""
        # Без фильтра шлём всё
        if not self.cities:
            return True
        allowed = {c.strip().lower() for c in self.cities.split(",") if c.strip()}
        return from_city.lower() in allowed or to_city.lower() in allowed

    def __repr__(self) -> str:
        return f"<PromoChat chat_id={self.chat_id} active={self.is_active}>"
