import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _smtp_password() -> str | None:
    host = (_env_value("SMTP_SERVER") or "").lower()
    password = _env_value("SMTP_PASSWORD")
    if not password:
        return None
    if "gmail" in host:
        return "".join(password.split())
    return password


def _mailer_enabled() -> bool:
    value = os.getenv("ENABLE_MAILER")
    if value is not None:
        return _env_flag("ENABLE_MAILER")
    return all(
        [
            _env_value("RESEND_API_KEY"),
        ]
    ) or all(
        [
            _env_value("SMTP_SERVER"),
            _env_value("SMTP_EMAIL"),
            _smtp_password(),
        ]
    )


class Config:
    SECRET_KEY = _env_value("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _env_value("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))

    SMTP_SERVER = _env_value("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL = _env_value("SMTP_EMAIL")
    SMTP_PASSWORD = _smtp_password()
    MAIL_USE_TLS = _env_flag("MAIL_USE_TLS")
    MAIL_USE_SSL = _env_flag("MAIL_USE_SSL")
    MAIL_DEBUG = int(os.getenv("MAIL_DEBUG", "0"))
    MAIL_DEFAULT_SENDER = _env_value("MAIL_DEFAULT_SENDER")
    MAIL_TRANSPORT = (_env_value("MAIL_TRANSPORT") or "auto").lower()
    RESEND_API_KEY = _env_value("RESEND_API_KEY")
    RESEND_API_URL = _env_value("RESEND_API_URL") or "https://api.resend.com/emails"
    ENABLE_MAILER = _mailer_enabled()
    SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "10"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(4 * 1024 * 1024)))
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
    STUDENT_UPLOAD_FOLDER = "uploads/students"
    BOOK_UPLOAD_FOLDER = "uploads/books"
    IMAGE_STORAGE_BACKEND = (_env_value("IMAGE_STORAGE_BACKEND") or "database").lower()

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY:
            raise RuntimeError("SECRET_KEY must be set before the application starts.")
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError("DATABASE_URI must be set before the application starts.")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


def get_config():
    environment = os.getenv("FLASK_ENV", "development").lower()
    if environment == "production":
        return ProductionConfig
    return DevelopmentConfig
