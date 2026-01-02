import os
from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp
from flask_jwt_extended import JWTManager
from database.models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Разрешаем фронтенд с разных источников
    # Получаем URL frontend из переменной окружения или используем список по умолчанию
    frontend_url = os.getenv("FRONTEND_URL", "")
    cors_origins = os.getenv("CORS_ORIGINS", "")
    
    # Формируем список разрешенных origins
    allowed_origins = [
        "http://localhost:5173",  # локальный dev
        "http://localhost:3000",  # альтернативный dev порт
        os.getenv("FRONTEND_URL", "https://classification-system.netlify.app"),  # production Netlify
    ]
    
    # Добавляем frontend URL если указан
    if frontend_url:
        allowed_origins.append(frontend_url)
    
    # Добавляем origins из CORS_ORIGINS (через запятую)
    if cors_origins:
        allowed_origins.extend([origin.strip() for origin in cors_origins.split(",")])
    
    # Если ничего не указано, разрешаем все (для разработки)
    # В production лучше указать конкретные URL
    if not frontend_url and not cors_origins:
        allowed_origins = ["*"]  # Разрешаем все для упрощения деплоя
    
    CORS(app,
         origins=allowed_origins if allowed_origins != ["*"] else None,  # None = разрешить все
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])

    db.init_app(app)
    JWTManager(app)

    # Автоматическая инициализация БД при первом запуске
    with app.app_context():
        try:
            # Проверяем, существует ли таблица users
            from database.models import User
            # Если таблицы не существуют, создаем их
            db.create_all()
            
            # Проверяем, есть ли админ, если нет - создаем
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', role='admin')
                default_password = os.getenv('ADMIN_DEFAULT_PASSWORD', 'admin123')
                admin.set_password(default_password)
                db.session.add(admin)
                db.session.commit()
                print("✅ База данных инициализирована автоматически")
                print(f"✅ Админ создан (username: admin, password: {default_password})")
        except Exception as e:
            print(f"⚠️  Ошибка при автоматической инициализации БД: {e}")
            # Продолжаем работу, возможно БД еще не готова

    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/health')
    def health():
        return {"status": "ok"}, 200

    return app
