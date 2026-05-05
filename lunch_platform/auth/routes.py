from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..core.auth import authenticate, change_password, check_login_rate, current_account, get_request_ip, login_required, login_user, logout_user, register_account
from ..core.db import log_event
from ..core.utils import normalize_email, normalize_person_name, normalize_spaces
from ..services.notifications import mark_notification_read

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = get_request_ip()
        if not check_login_rate(ip):
            flash("Too many login attempts. Try again later.", "error")
            return redirect(url_for("auth.login"))

        identifier = (
            request.form.get("username")
            or request.form.get("identifier")
            or request.form.get("email")
            or ""
        ).strip()
        password = request.form.get("password", "")

        account = authenticate(identifier, password)
        if not account:
            log_event("login_failed", actor=identifier, detail=f"ip={ip}")
            flash("Neplatné přihlašovací údaje.", "error")
            return redirect(url_for("auth.login"))

        login_user(account)

        if account["must_change_password"]:
            flash("Změna hesla je vyžadována.", "error")
            return redirect(url_for("orders.profile", _anchor="password-change"))

        next_url = request.form.get("next") or request.args.get("next") or url_for("orders.index")
        return redirect(next_url)

    return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if not current_app.config.get("ALLOW_SELF_REGISTRATION", True):
        flash("Self-registration is disabled.", "error")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        first_name = normalize_person_name(request.form.get("first_name", ""))
        last_name = normalize_person_name(request.form.get("last_name", ""))
        email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        if not first_name or not last_name or not email or len(password) < 8:
            flash("Vyplňte křestní jméno, příjmení, e-mail a heslo alespoň o 8 znacích.", "error")
            return redirect(url_for("auth.register"))
        if password != password_confirm:
            flash("Hesla se neshodují.", "error")
            return redirect(url_for("auth.register"))
        try:
            register_account(first_name, last_name, email, password)
        except Exception:
            flash("Registrace se nepodařila. E-mail už možná existuje.", "error")
            return redirect(url_for("auth.register"))
        flash("Účet byl vytvořen. Přihlaste se.")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    flash("Odhlášeno.")
    return redirect(url_for("auth.login"))


@bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def read_notification(notification_id: int):
    account = current_account()
    mark_notification_read(account['id'], notification_id)
    target = request.form.get('next') or url_for('orders.profile', _anchor='password-change')
    return redirect(target)


@bp.route('/profile/password', methods=['POST'])
@login_required
def update_password():
    account = current_account()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    if len(new_password) < 8:
        flash('Nové heslo musí mít alespoň 8 znaků.', 'error')
        return redirect(url_for('orders.profile', _anchor='password-change'))
    if new_password != confirm_password:
        flash('Nová hesla se neshodují.', 'error')
        return redirect(url_for('orders.profile', _anchor='password-change'))
    if not change_password(account['id'], current_password, new_password):
        flash('Aktuální heslo není správné.', 'error')
        return redirect(url_for('orders.profile', _anchor='password-change'))
    flash('Heslo bylo změněno.')
    return redirect(url_for('orders.profile', _anchor='password-change'))
