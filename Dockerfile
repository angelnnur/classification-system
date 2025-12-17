FROM python:3.11-slim

WORKDIR /app

# Копируем requirements из backend
COPY backend/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем backend код
COPY backend/src ./backend/src

# Устанавливаем переменные окружения
ENV FLASK_ENV=production
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV PYTHONUNBUFFERED=1

# Запускаем Flask
CMD ["python", "-m", "flask", "--app=backend.src.app", "run", "--host=0.0.0.0", "--port=5000"]
