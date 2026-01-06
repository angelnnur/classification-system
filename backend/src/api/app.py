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
    
    cors_origins = os.getenv("CORS_ORIGINS", "")
    
    # Формируем список разрешенных origins
    allowed_origins = [
        "http://localhost:5173"
    ]
    
    if cors_origins:
        allowed_origins.extend([origin.strip() for origin in cors_origins.split(",")])
    
    if cors_origins:
        print(f"🔒 CORS настроен для origins: {allowed_origins}")
        CORS(app,
             origins=allowed_origins,
             supports_credentials=True,
             allow_headers=["Content-Type", "Authorization"],
             methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])
    else:
        print("🌐 CORS разрешает все origins (для упрощения деплоя)")
        CORS(app,
             origins="*",  # Разрешаем все для упрощения
             supports_credentials=False,  # Не поддерживаем credentials при "*"
             allow_headers=["Content-Type", "Authorization"],
             methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/health')
    def health():
        return {"status": "ok"}, 200

    return app
