FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Зависимости Python (бот использует те же + aiogram)
COPY backend/requirements.txt /app/backend/requirements.txt
COPY bot/requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r bot/requirements.txt

# Копируем код
COPY shared/ /app/shared/
COPY backend/ /app/backend/
COPY bot/ /app/bot/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini

CMD ["python", "-m", "bot.main"]
