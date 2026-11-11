import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PADRAO = (BASE_DIR / "instance" / "helpdesk.db").as_posix()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-troque-esta-chave")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PADRAO}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SEED_ENABLED = True
    SEED_SENHA_PADRAO = os.environ.get("SEED_SENHA_PADRAO", "Demo@2026")
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SEED_ENABLED = False


class ProductionConfig(Config):
    # Sem SECRET_KEY definida, gera uma aleatória (sessões caem a cada reinício).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
