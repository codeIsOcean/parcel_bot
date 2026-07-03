"""Seed-скрипт для заполнения таблицы городов."""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from backend.app.database import async_session_factory
from shared.models.city import City


CITIES = [
    # name_en, name_ru, name_kz, country_code, flag, sort_order
    ("Dubai", "Дубай", "Дубай", "AE", "🇦🇪", 1),
    ("Almaty", "Алматы", "Алматы", "KZ", "🇰🇿", 2),
    ("Moscow", "Москва", "Мәскеу", "RU", "🇷🇺", 3),
    ("Istanbul", "Стамбул", "Стамбұл", "TR", "🇹🇷", 4),
    ("Astana", "Астана", "Астана", "KZ", "🇰🇿", 5),
    ("New York", "Нью-Йорк", "Нью-Йорк", "US", "🇺🇸", 6),
    ("London", "Лондон", "Лондон", "GB", "🇬🇧", 10),
    ("Seoul", "Сеул", "Сеул", "KR", "🇰🇷", 11),
    ("Bangkok", "Бангкок", "Бангкок", "TH", "🇹🇭", 12),
    ("Antalya", "Анталья", "Анталия", "TR", "🇹🇷", 13),
    ("Tbilisi", "Тбилиси", "Тбилиси", "GE", "🇬🇪", 14),
    ("Bishkek", "Бишкек", "Бішкек", "KG", "🇰🇬", 15),
    ("Tashkent", "Ташкент", "Ташкент", "UZ", "🇺🇿", 16),
    ("Shymkent", "Шымкент", "Шымкент", "KZ", "🇰🇿", 17),
    ("Aktau", "Актау", "Ақтау", "KZ", "🇰🇿", 18),
    ("Beijing", "Пекин", "Пекин", "CN", "🇨🇳", 20),
    ("Tokyo", "Токио", "Токио", "JP", "🇯🇵", 21),
    ("Paris", "Париж", "Париж", "FR", "🇫🇷", 22),
    ("Berlin", "Берлин", "Берлин", "DE", "🇩🇪", 23),
    ("Milan", "Милан", "Милан", "IT", "🇮🇹", 24),
]


async def seed():
    async with async_session_factory() as session:
        for name_en, name_ru, name_kz, country_code, flag, sort_order in CITIES:
            # Проверяем, не существует ли уже
            result = await session.execute(
                select(City).where(City.name_en == name_en)
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  skip: {name_en} (already exists)")
                continue

            city = City(
                name_en=name_en,
                name_ru=name_ru,
                name_kz=name_kz,
                country_code=country_code,
                flag=flag,
                is_active=True,
                sort_order=sort_order,
            )
            session.add(city)
            print(f"  add:  {flag} {name_en} / {name_ru}")

        await session.commit()
        print(f"\nDone! Seeded {len(CITIES)} cities.")


if __name__ == "__main__":
    asyncio.run(seed())
