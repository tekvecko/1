from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def app(tmp_path):
    flask = pytest.importorskip("flask")
    from lunch_platform import create_app
    from lunch_platform.core.db import execute

    database_path = tmp_path / "test.db"
    app = create_app({
        "TESTING": True,
        "ENV_NAME": "development",
        "DATABASE_PATH": str(database_path),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "LOG_FOLDER": str(tmp_path / "logs"),
        "SECRET_KEY": "dev-secret-for-tests-only",
    })
    with app.app_context():
        execute("INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES ('Pondělí', 'Kuřecí řízek', '150 Kč', 15000)")
        execute("INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES ('Úterý', 'Hovězí guláš', '165 Kč', 16500)")
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def get_csrf(client, path: str) -> str:
    client.get(path)
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def register(client, email: str, first_name: str, last_name: str, password: str = "supersecret"):
    csrf = get_csrf(client, "/register")
    return client.post("/register", data={
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "password_confirm": password,
        "csrf_token": csrf,
    }, follow_redirects=True)


def login(client, identifier: str, password: str = "supersecret"):
    csrf = get_csrf(client, "/login")
    return client.post("/login", data={
        "username": identifier,
        "password": password,
        "csrf_token": csrf,
    }, follow_redirects=False)
