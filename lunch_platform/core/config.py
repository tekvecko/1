from __future__ import annotations

import os
from pathlib import Path


class Config:
    def __init__(self) -> None:
        base = Path(os.environ.get("LUNCH_BASE_DIR", Path.cwd()))
        instance = base / "instance"
        env_name = os.environ.get("FLASK_ENV", "development").lower()
        default_secret = "dev-insecure-change-me-in-production"

        self.ENV_NAME = env_name
        self.DEBUG = env_name == "development"
        self.TESTING = False
        self.SECRET_KEY = os.environ.get("SECRET_KEY", default_secret)
        self.DATABASE_PATH = os.environ.get("DATABASE_PATH", str(instance / "lunch_platform.db"))
        self.UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(base / "uploads"))
        self.LOG_FOLDER = os.environ.get("LOG_FOLDER", str(base / "logs"))
        self.MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "8")) * 1024 * 1024
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        self.SESSION_COOKIE_SECURE = env_name != "development"
        self.SESSION_COOKIE_NAME = "__Host-session" if env_name != "development" else "session"
        self.PERMANENT_SESSION_LIFETIME_HOURS = int(os.environ.get("SESSION_HOURS", "8"))
        self.ADMIN_BOOTSTRAP_PASSWORD = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
        self.ALLOW_SELF_REGISTRATION = os.environ.get("ALLOW_SELF_REGISTRATION", "1") == "1"
        self.DB_VERSION = 2
