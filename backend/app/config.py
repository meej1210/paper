import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devsecops-local-secret-key-2026-demo")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "devsecops-local-jwt-secret-key-2026-demo")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "12")))
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'devsecops.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    REPORT_DIR = os.getenv("REPORT_DIR", str(BASE_DIR / "reports"))
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
    ALLOWED_UPLOAD_EXTENSIONS = tuple(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".py,.zip,.tar.gz").split(",")
        if ext.strip()
    )
    SAST_DEFAULT_ENGINE = os.getenv("SAST_DEFAULT_ENGINE", "bandit").strip().lower()
    SAST_ALLOWED_ENGINES = tuple(
        engine.strip().lower()
        for engine in os.getenv("SAST_ALLOWED_ENGINES", "bandit,semgrep").split(",")
        if engine.strip()
    )
    SEMGREP_CMD = os.getenv("SEMGREP_CMD", "semgrep")
    SEMGREP_RULESET = os.getenv("SEMGREP_RULESET", "p/python")
    SCA_SCANNER_CMD = os.getenv("SCA_SCANNER_CMD", "")
    SCA_ALLOWED_EXTENSIONS = tuple(
        ext.strip().lower()
        for ext in os.getenv("SCA_ALLOWED_EXTENSIONS", ".txt,.zip").split(",")
        if ext.strip()
    )
    SCA_MAX_UPLOAD_MB = int(os.getenv("SCA_MAX_UPLOAD_MB", "20"))
    SCA_SCAN_TIMEOUT = int(os.getenv("SCA_SCAN_TIMEOUT", "120"))
    DEFAULT_DAST_TIMEOUT = int(os.getenv("DEFAULT_DAST_TIMEOUT", "60"))
    MAX_DAST_TIMEOUT = int(os.getenv("MAX_DAST_TIMEOUT", "600"))
    DAST_SCANNER_CMD = os.getenv("DAST_SCANNER_CMD", "wapiti")
    DAST_ALLOWED_HOSTS = tuple(
        host.strip().lower()
        for host in os.getenv("DAST_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
        if host.strip()
    )
    DAST_ALLOW_PRIVATE_NETWORKS = os.getenv("DAST_ALLOW_PRIVATE_NETWORKS", "true").lower() == "true"
    DAST_ALLOW_PUBLIC_TARGETS = os.getenv("DAST_ALLOW_PUBLIC_TARGETS", "false").lower() == "true"
    DAST_DEFAULT_SCOPE = os.getenv("DAST_DEFAULT_SCOPE", "folder")
    DAST_MODULES = os.getenv("DAST_MODULES", "common")
    DAST_REQUEST_TIMEOUT = int(os.getenv("DAST_REQUEST_TIMEOUT", "6"))
    DAST_MAX_SCAN_TIME = int(os.getenv("DAST_MAX_SCAN_TIME", "60"))
    DAST_MAX_ATTACK_TIME = int(os.getenv("DAST_MAX_ATTACK_TIME", "15"))
    DAST_PUBLIC_SCOPE = os.getenv("DAST_PUBLIC_SCOPE", "url")
    DAST_PUBLIC_MAX_TIMEOUT = int(os.getenv("DAST_PUBLIC_MAX_TIMEOUT", "60"))
    DAST_PUBLIC_MAX_SCAN_TIME = int(os.getenv("DAST_PUBLIC_MAX_SCAN_TIME", "20"))
    DAST_PUBLIC_MAX_ATTACK_TIME = int(os.getenv("DAST_PUBLIC_MAX_ATTACK_TIME", "5"))
    DAST_PUBLIC_REQUEST_TIMEOUT = int(os.getenv("DAST_PUBLIC_REQUEST_TIMEOUT", "3"))
    TASK_CREATE_RATE_LIMIT = os.getenv("TASK_CREATE_RATE_LIMIT", "60 per minute")
    QUEUE_STABILITY_WINDOW_HOURS = int(os.getenv("QUEUE_STABILITY_WINDOW_HOURS", "24"))
    CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    AI_API_BASE = os.getenv("AI_API_BASE", "https://api.deepseek.com")
    AI_API_KEY = os.getenv("AI_API_KEY")
    AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")
    AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "25"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"
    DAST_ALLOWED_HOSTS = ("127.0.0.1", "localhost")
    DAST_ALLOW_PRIVATE_NETWORKS = True
    DAST_ALLOW_PUBLIC_TARGETS = False
    DAST_PUBLIC_MAX_TIMEOUT = 60


class ProductionConfig(Config):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None):
    name = config_name or os.getenv("FLASK_ENV", "development")
    return CONFIG_MAP.get(name, DevelopmentConfig)
