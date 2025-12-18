FROM python:3.11-slim

WORKDIR /app

# Копируем requirements
COPY backend/requirements.txt .

# Добавляем gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Копируем весь backend код
COPY backend/src ./backend/src

# Устанавливаем переменные окружения
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=5000

# Экспонируем порт
EXPOSE 5000

# Запускаем через gunicorn (4 worker'а)
CMD cd /app/backend/src && gunicorn --workers=2 --worker-class=sync --bind=0.0.0.0:5000 --timeout=60 --access-logfile=- --error-logfile=- "api.app:create_app()"
