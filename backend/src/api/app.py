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
    allowed_origins = [
        "http://localhost:5173",  # локальный dev
        "http://localhost:3000",  # альтернативный dev порт
        os.getenv("FRONTEND_URL", "https://classification-system.netlify.app"),  # production Netlify
    ]
    
    CORS(app,
         origins=allowed_origins,
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/health')
    def health():
        return {"status": "ok"}, 200

    return app
