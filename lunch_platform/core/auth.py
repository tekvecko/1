from __future__ import annotations

import functools
import secrets
import time
from collections import defaultdict

from flask import abort, current_app, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import account_full_name, execute, log_event, query
from .utils import full_name_from_parts, name_to_initials, normalize_email
from ..services.notifications import list_notifications, sync_password_change_notification, unread_notification_count

ROLE_HIERARCHY = {"user": 0, "manager": 1, "billing_admin": 2, "super_admin": 3}
_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_LOGIN_WINDOW = 300
_LOGIN_MAX = 10


def get_request_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() if fwd else (request.remote_addr or "unknown")


def check_login_rate(ip: str) -> bool:
    if current_app.config.get("TESTING"):
        _LOGIN_ATTEMPTS.clear()
        return True

    now = time.monotonic()
    valid = [t for t in _LOGIN_ATTEMPTS[ip] if now - t < _LOGIN_WINDOW]
    valid.append(now)
    _LOGIN_ATTEMPTS[ip] = valid
    return len(valid) <= _LOGIN_MAX


def current_account():
    aid = session.get("account_id")
    if not aid:
        g.account_id = None
        g.role = None
        return None
    acct = query("SELECT * FROM accounts WHERE id=? AND is_active=1", (aid,), one=True)
    g.account_id = acct["id"] if acct else None
    g.role = acct["role"] if acct else None
    return acct


def current_user_name() -> str:
    acct = current_account()
    return account_full_name(acct) if acct else ""


def login_user(account) -> None:
    session.clear()
    session.permanent = True
    session["account_id"] = account["id"]
    session["role"] = account["role"]
    session["must_change_password"] = bool(account["must_change_password"])
    session["csrf_token"] = secrets.token_urlsafe(32)
    execute("UPDATE accounts SET last_login_at=CURRENT_TIMESTAMP WHERE id=?", (account["id"],))
    log_event("login", account_id=account["id"], actor=account_full_name(account), role=account["role"])


def logout_user() -> None:
    acct = current_account()
    if acct:
        log_event("logout", account_id=acct["id"], actor=account_full_name(acct), role=acct["role"])
    session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not current_account():
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def require_role(min_role: str):
    def decorator(view):
        @functools.wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            acct = current_account()
            if ROLE_HIERARCHY.get(acct["role"], -1) < ROLE_HIERARCHY[min_role]:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def verify_csrf() -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected = session.get("csrf_token")
        if not sent or not expected or sent != expected:
            abort(403)


def authenticate(identifier: str, password: str):
    raw_ident = (identifier or "").strip()
    username_ident = raw_ident.lower()
    email_ident = normalize_email(raw_ident) or username_ident

    acct = query(
        "SELECT * FROM accounts WHERE (lower(username)=lower(?) OR lower(email)=lower(?)) AND is_active=1",
        (username_ident, email_ident),
        one=True,
    )
    if acct and check_password_hash(acct["password_hash"], password):
        return acct
    return None


def register_account(first_name: str, last_name: str, email: str, password: str, role: str = "user"):
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = normalize_email(email)
    display_name = full_name_from_parts(first_name, last_name)
    cur = execute(
        "INSERT INTO accounts(username, display_name, first_name, last_name, email, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
        (email, display_name, first_name, last_name, email, generate_password_hash(password), role),
    )
    account_id = cur.lastrowid
    execute("INSERT OR IGNORE INTO users(account_id, allergens) VALUES(?, '')", (account_id,))
    return query("SELECT * FROM accounts WHERE id=?", (account_id,), one=True)


def change_password(account_id: int, current_password: str, new_password: str) -> bool:
    acct = query("SELECT * FROM accounts WHERE id=?", (account_id,), one=True)
    if not acct or not check_password_hash(acct["password_hash"], current_password):
        return False
    execute("UPDATE accounts SET password_hash=?, must_change_password=0 WHERE id=?", (generate_password_hash(new_password), account_id))
    acct = query("SELECT * FROM accounts WHERE id=?", (account_id,), one=True)
    sync_password_change_notification(acct)
    log_event("password_changed", account_id=account_id, actor=account_full_name(acct), role=acct["role"])
    return True


def init_auth(app) -> None:
    @app.before_request
    def _csrf_and_timeout():
        acct = current_account()
        if acct:
            sync_password_change_notification(acct)
            last_active = session.get("last_active", time.time())
            timeout = current_app.config.get("PERMANENT_SESSION_LIFETIME_HOURS", 8) * 3600
            if time.time() - last_active > timeout:
                session.clear()
                flash("Session expired. Please sign in again.", "error")
                return redirect(url_for("auth.login", next=request.path))
            session["last_active"] = time.time()
        verify_csrf()

    @app.context_processor
    def _inject_auth_helpers():
        acct = current_account()
        notifications = list_notifications(acct["id"], unread_only=True) if acct else []
        return {
            "csrf_token": csrf_token,
            "current_account": acct,
            "current_role": acct["role"] if acct else None,
            "current_account_name": account_full_name(acct) if acct else "",
            "current_account_initials": name_to_initials(acct["first_name"], acct["last_name"]) if acct else "",
            "current_notifications": notifications,
            "current_notification_count": unread_notification_count(acct["id"]) if acct else 0,
        }

    @app.errorhandler(403)
    def _forbidden(_error):
        return "Access denied", 403

    @app.errorhandler(404)
    def _not_found(_error):
        return "Not found", 404

    @app.errorhandler(500)
    def _server_error(_error):
        current_app.logger.exception("Unhandled exception")
        return "Internal server error", 500
