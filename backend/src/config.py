import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='/mnt/d/University/ВКР/classification-system/backend/.env.example')

class Config:
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'TRUE')
    HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:1234@localhost:5432/product_classifier')
    SECRET_KEY = os.getenv('SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = DB_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret")

    UPLOAD_FOLDER = "src/data/uploads"
    PROCESSED_FOLDER = "src/data/processed"
    MODELS_BIN = "src/data/models_bin"