from __future__ import annotations

import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from uuid import uuid4

from flask import current_app, g, request


SAFE_INLINE_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self';"
)


def security_preflight(app) -> None:
    env_name = app.config.get("ENV_NAME", "production")
    secret_key = app.config.get("SECRET_KEY", "") or ""
    if env_name != "development":
        if secret_key == "dev-insecure-change-me-in-production" or len(secret_key) < 32:
            raise RuntimeError(
                "FATAL: SECRET_KEY is not set or uses the insecure default value. "
                "Set a strong SECRET_KEY before starting the app in production."
            )


def configure_logging(app) -> None:
    Path(app.config["LOG_FOLDER"]).mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        os.path.join(app.config["LOG_FOLDER"], "lunch_platform.log"),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.handlers = []
    app.logger.addHandler(handler)


def init_security(app) -> None:
    security_preflight(app)
    configure_logging(app)

    @app.before_request
    def _before_request():
        g.request_started_at = time.perf_counter()
        g.request_id = uuid4().hex[:12]

    @app.after_request
    def _after_request(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        if app.config.get("ENV_NAME") != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = SAFE_INLINE_CSP
        duration_ms = int((time.perf_counter() - getattr(g, "request_started_at", time.perf_counter())) * 1000)
        account_id = getattr(g, "account_id", None)
        role = getattr(g, "role", None)
        app.logger.info(
            "request_id=%s method=%s path=%s status=%s account_id=%s role=%s ip=%s duration_ms=%s",
            g.request_id,
            request.method,
            request.path,
            response.status_code,
            account_id,
            role,
            request.headers.get("X-Forwarded-For", request.remote_addr),
            duration_ms,
        )
        return response
