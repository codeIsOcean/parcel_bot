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

    # Публичный @username чата (у приватных групп его нет)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Тип чата в Telegram: group / supergroup / channel
    chat_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Кто добавил чат в рассылку
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Состоит ли бот в чате сейчас. Снимается, когда бота выгнали (my_chat_member).
    is_member: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Что публиковать в этот чат: посылки («нужно отправить») и/или рейсы («лечу»)
    post_parcels: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    post_flights: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    @property
    def can_post(self) -> bool:
        """Можно ли сейчас слать в чат: включён и бот всё ещё в нём."""
        return bool(self.is_active and self.is_member)

    def __repr__(self) -> str:
        return f"<PromoChat chat_id={self.chat_id} active={self.is_active}>"


class GroupPost(Base, TimestampMixin):
    """Объявление, опубликованное ботом в группе.

    Хранит message_id, чтобы при закрытии посылки или рейса пост можно было
    отредактировать: убрать кнопку и пометить «закрыто».
    """
    __tablename__ = "group_posts"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Куда ушло объявление
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # ID сообщения в этом чате
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Что опубликовано: "parcel" или "flight"
    kind: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # ID посылки или рейса
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Пост уже помечен закрытым — второй раз не редактируем
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<GroupPost {self.kind}#{self.entity_id} chat={self.chat_id} msg={self.message_id}>"
