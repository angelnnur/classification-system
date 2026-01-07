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
# Настройка TensorFlow для CPU и отключения GPU
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV CUDA_VISIBLE_DEVICES=-1
ENV TF_FORCE_GPU_ALLOW_GROWTH=false

# Открытие порта (Render.com использует переменную PORT)
EXPOSE ${PORT:-5001}

# Команда запуска через gunicorn
# Render.com предоставляет переменную PORT через окружение
# Используем 1 worker для экономии памяти на бесплатном плане (512MB)
# Используем shell форму для подстановки переменной PORT
CMD sh -c 'gunicorn --bind 0.0.0.0:${PORT:-5001} --chdir src main:app'