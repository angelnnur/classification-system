# Backend Dockerfile
FROM python:3.12-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY src/ ./src/

# Создание необходимых директорий
RUN mkdir -p src/data/uploads src/data/processed src/data/plots

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=src/main.py

# Открытие порта (Render.com использует переменную PORT)
EXPOSE ${PORT:-5001}

# Команда запуска через gunicorn
# Render.com предоставляет переменную PORT, используем её или 5001 по умолчанию
CMD gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 4 --timeout 120 --chdir src wsgi:app

