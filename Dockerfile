FROM python:3.11-slim

WORKDIR /app

# Копируем requirements
COPY backend/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь backend код
COPY backend/src ./backend/src

# Устанавливаем переменные окружения
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Меняем рабочую директорию в backend
WORKDIR /app/backend/src

# Запускаем приложение
CMD ["python", "main.py"]
