FROM python:3.12-slim

# Отключаем буферизацию вывода и генерацию .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода проекта
COPY . .

# Команда запуска (применяет миграции Alembic и запускает бота)
CMD ["sh", "-c", "alembic upgrade head && python -m bot.main"]
