import os
from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp
from api.feedback import feedback_bp
from flask_jwt_extended import JWTManager
from database.models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    production_frontend_url = os.getenv("CORS_ORIGINS", "")
    
    allowed_frontend_urls = [
        "http://localhost:5173" #local frontend url
    ]
    
    if production_frontend_url:
        allowed_frontend_urls.extend([origin.strip() for origin in production_frontend_url.split(",")])
    
    CORS(app,
        origins=allowed_frontend_urls,
        supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"])

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(feedback_bp, url_prefix='/api')

    @app.route('/health')
    def health():
        return {"status": "ok"}, 200

    return app
