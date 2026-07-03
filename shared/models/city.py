from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from shared.models.base import Base


class City(Base):
    """Город — справочник городов для маршрутов."""
    __tablename__ = "cities"

    # Уникальный ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Название на английском (используется как ключ)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # Название на русском
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)

    # Название на казахском
    name_kz: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Код страны (ISO 3166-1 alpha-2)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # Эмодзи флаг страны
    flag: Mapped[str] = mapped_column(String(10), nullable=False)

    # Активен (показывать в списке)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Порядок сортировки (популярные первые)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    def __repr__(self) -> str:
        return f"<City id={self.id} name={self.name_en}>"
