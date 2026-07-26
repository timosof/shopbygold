import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)


def _resolve_database_uri():
    configured_uri = os.getenv("DATABASE_URL")
    if configured_uri:
        return configured_uri

    db_path = os.path.join(BASE_DIR, "shopbygold.db")
    return f"sqlite:///{db_path.replace(os.sep, '/')}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "shopbygold-dev-secret")
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "shopbygold-jwt-secret")
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_placeholder")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5000")

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "False").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "True").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    MAIL_USERNAME = os.getenv("MAIL_USERNAME") or os.getenv("EMAIL_ADDRESS")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or os.getenv("EMAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "ShopByGold")
    
    SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 5,
    "max_overflow": 10,
    }
