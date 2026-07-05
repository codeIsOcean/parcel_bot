FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Зависимости Python
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Копируем код
COPY shared/ /app/shared/
COPY backend/ /app/backend/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini

# Запуск: миграции + uvicorn
ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
