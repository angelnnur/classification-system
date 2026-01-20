import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False')
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5001))
    DB_URL = os.getenv('DATABASE_URL', '')
    SECRET_KEY = os.getenv('SECRET_KEY', '')

    SQLALCHEMY_DATABASE_URI = DB_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

    UPLOAD_FOLDER = "src/data/uploads"
    PROCESSED_FOLDER = "src/data/processed"
    MODELS_BIN = "src/data/models_bin"

    WILDBERRIES_API_KEY = os.getenv("WILDBERRIES_API_KEY", None)
    OZON_MGT_API_KEY = os.getenv("OZON_MGT_API_KEY", None)
    OZON_MGT_CLIENT_ID = os.getenv("OZON_MGT_CLIENT_ID", None)
    OZON_KGT_API_KEY = os.getenv("OZON_KGT_API_KEY", None)
    OZON_KGT_CLIENT_ID = os.getenv("OZON_KGT_CLIENT_ID", None)
    YM_API_TOKEN=os.getenv("YM_API_TOKEN", None)
    YM_BUSINESS_ID=os.getenv("YM_BUSINESS_ID", None)
