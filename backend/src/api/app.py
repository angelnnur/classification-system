from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp
from flask_jwt_extended import JWTManager
from database.models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app,
         origins=["http://localhost:5173"],
         supports_credentials=False,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "DELETE"])

    db.init_app(app)
    JWTManager(app)

    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/health')
    def health():
        return {"status": "ok"}, 200

    return app
