from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from flask import current_app, g
from werkzeug.security import generate_password_hash

from .utils import full_name_from_parts


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '' UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
);

CREATE TABLE IF NOT EXISTS users (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
    allergens TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    link_url TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL DEFAULT 'info',
    kind TEXT NOT NULL DEFAULT 'generic',
    dedupe_key TEXT NOT NULL DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME
);


CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    dish_name TEXT NOT NULL,
    price_text TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL DEFAULT 0,
    image_url TEXT NOT NULL DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    restaurant_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by_account_id INTEGER NOT NULL REFERENCES accounts(id),
    day TEXT NOT NULL,
    dish_id INTEGER REFERENCES menu(id),
    status TEXT NOT NULL DEFAULT 'draft',
    dish_name_snapshot TEXT NOT NULL DEFAULT '',
    price_snapshot_text TEXT NOT NULL DEFAULT '',
    price_snapshot_cents INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finalized_at DATETIME,
    locked_at DATETIME,
    paid_at DATETIME,
    cancelled_at DATETIME,
    payment_status TEXT NOT NULL DEFAULT 'unpaid',
    paid_amount_cents INTEGER NOT NULL DEFAULT 0,
    confirmed_at DATETIME,
    payment_note TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    restaurant_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER REFERENCES accounts(id),
    created_by_account_id INTEGER REFERENCES accounts(id),
    dish_id INTEGER REFERENCES menu(id),
    dish_name TEXT NOT NULL DEFAULT '',
    rating INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    value INTEGER NOT NULL DEFAULT 0,
    comment TEXT NOT NULL DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL DEFAULT '',
    account_id INTEGER,
    actor TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    target TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_account_id ON audit_log(account_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);

CREATE INDEX IF NOT EXISTS idx_ratings_account_id ON ratings(account_id);
CREATE INDEX IF NOT EXISTS idx_ratings_created_by_account_id ON ratings(created_by_account_id);
CREATE INDEX IF NOT EXISTS idx_ratings_dish_id ON ratings(dish_id);

CREATE INDEX IF NOT EXISTS idx_menu_day ON menu(day);
CREATE INDEX IF NOT EXISTS idx_notifications_account_unread ON notifications(account_id, read_at);
CREATE INDEX IF NOT EXISTS idx_orders_account_status ON orders(created_by_account_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_account_payment_status ON orders(created_by_account_id, payment_status);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant_status ON orders(restaurant_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant_account_day ON orders(restaurant_id, created_by_account_id, day);
CREATE INDEX IF NOT EXISTS idx_menu_restaurant_day ON menu(restaurant_id, day, id);

"""


class CursorResult:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid if lastrowid is not None else getattr(cursor, "lastrowid", None)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


def database_url() -> str:
    return (current_app.config.get("DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()


def db_kind() -> str:
    url = database_url()
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        return "postgres"
    return "sqlite"


def is_postgres() -> bool:
    return db_kind() == "postgres"


def _convert_placeholders(sql: str) -> str:
    # Project SQL uses SQLite-style '?' placeholders.
    # Psycopg requires '%s'. Application SQL does not use literal '?' in DB statements.
    return sql.replace("?", "%s")


def _convert_sqlite_ddl_to_postgres(sql: str) -> str:
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("DATETIME", "TIMESTAMP")
    sql = re.sub(r"\s+COLLATE\s+NOCASE", "", sql, flags=re.I)
    return sql


def _convert_sqlite_dml_to_postgres(sql: str) -> str:
    stripped = " ".join(sql.strip().split()).upper()

    if stripped.startswith("INSERT OR REPLACE INTO SETTINGS"):
        return (
            "INSERT INTO settings(key, value) VALUES(%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value"
        )

    if stripped.startswith("INSERT OR IGNORE INTO USERS"):
        sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.I)
        sql = _convert_placeholders(sql)
        return sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    sql = _convert_placeholders(sql)

    # lastrowid compatibility for inserts that are followed by cur.lastrowid.
    if re.match(r"\s*INSERT\s+INTO\s+(accounts|restaurants)\b", sql, flags=re.I) and "RETURNING" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"

    return sql


def adapt_sql(sql: str) -> str:
    if not is_postgres():
        return sql

    upper = sql.lstrip().upper()
    if upper.startswith("CREATE TABLE") or upper.startswith("CREATE INDEX") or upper.startswith("ALTER TABLE"):
        return _convert_placeholders(_convert_sqlite_ddl_to_postgres(sql))

    return _convert_sqlite_dml_to_postgres(sql)


def get_db():
    if "db" in g:
        return g.db

    if is_postgres():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except Exception as exc:
            raise RuntimeError(
                "DATABASE_URL is PostgreSQL, but psycopg is not installed. "
                "Install dependency: pip install 'psycopg[binary]'"
            ) from exc

        conn = psycopg.connect(database_url(), row_factory=dict_row)
        g.db = conn
        g.db_kind = "postgres"
        return conn

    db_path = Path(current_app.config["DATABASE_PATH"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    g.db = conn
    g.db_kind = "sqlite"
    return conn


@contextmanager
def cursor(write: bool = False):
    conn = get_db()
    cur = conn.cursor()
    try:
        yield cur
        if write:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def query(sql: str, params: tuple = (), *, one: bool = False):
    cur = get_db().execute(adapt_sql(sql), params)
    rows = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return rows


def execute(sql: str, params: tuple = ()):
    conn = get_db()
    cur = conn.execute(adapt_sql(sql), params)

    lastrowid = None
    if is_postgres() and "RETURNING ID" in adapt_sql(sql).upper():
        row = cur.fetchone()
        if row:
            lastrowid = row["id"] if isinstance(row, dict) else row[0]

    conn.commit()
    return CursorResult(cur, lastrowid=lastrowid)


def run_schema(conn, schema_sql: str) -> None:
    if not is_postgres():
        conn.executescript(schema_sql)
        return

    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
    for stmt in statements:
        conn.execute(adapt_sql(stmt))
    conn.commit()


def table_columns(table: str) -> set[str]:
    if is_postgres():
        rows = query(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_name=? ORDER BY ordinal_position",
            (table,),
        )
        return {row["name"] for row in rows}

    rows = query(f"PRAGMA table_info({table})")
    return {row["name"] for row in rows}


def get_setting(key: str, default: str = "") -> str:
    row = query("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, value))


def log_event(event_type: str, *, account_id: int | None = None, actor: str = "", role: str = "", target: str = "", detail: str = "") -> None:
    execute(
        "INSERT INTO audit_log(event_type, account_id, actor, role, target, detail) VALUES(?, ?, ?, ?, ?, ?)",
        (event_type, account_id, actor, role, target, detail),
    )


def account_full_name(account) -> str:
    if account is None:
        return ""
    return full_name_from_parts(account["first_name"], account["last_name"]) or account["display_name"]


def bootstrap_super_admin() -> None:
    admin = query("SELECT id FROM accounts WHERE lower(username)='admin'", one=True)
    if admin:
        return

    password = current_app.config.get("ADMIN_BOOTSTRAP_PASSWORD") or "heslo123"

    execute(
        """
        INSERT INTO accounts(username, display_name, first_name, last_name, email, password_hash, must_change_password, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'super_admin', 1)
        """,
        ("admin", "System Admin", "System", "Admin", "admin@local.invalid", generate_password_hash(password)),
    )

    admin = query("SELECT id, first_name, last_name, display_name, role FROM accounts WHERE username='admin'", one=True)

    execute("INSERT OR IGNORE INTO users(account_id, allergens) VALUES(?, '')", (admin["id"],))

    execute(
        "INSERT INTO notifications(account_id, title, body, link_url, level, kind, dedupe_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            admin["id"],
            "Změňte výchozí heslo",
            "Používáte výchozí heslo admin / heslo123. Změňte ho co nejdříve.",
            "/profile#password-change",
            "warning",
            "security",
            "password_change_required",
        ),
    )

    current_app.logger.warning("Bootstrap admin created: username=admin password=%s", password)


def init_db() -> None:
    conn = get_db()
    run_schema(conn, SCHEMA_SQL)
    set_setting("db_version", str(current_app.config["DB_VERSION"]))
    set_setting("lock_state", get_setting("lock_state", "auto"))
    set_setting("lock_time", get_setting("lock_time", "10:00"))
    bootstrap_super_admin()


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    g.pop("db_kind", None)
    if db is not None:
        db.close()


def init_app(app) -> None:
    @app.teardown_appcontext
    def _close_db(error=None):
        close_db(error)

    with app.app_context():
        init_db()
