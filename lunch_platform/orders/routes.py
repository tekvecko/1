from __future__ import annotations

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from ..core.auth import current_account, login_required
from ..core.db import execute, query
from ..core.utils import get_week_dates
from ..services.imports import get_current_menu_pdf_meta
from ..services.orders import (
    build_menu_view_model,
    current_state,
    get_user_orders,
    place_order,
    cancel_order,
    rate_dish,
)

bp = Blueprint("orders", __name__)


@bp.route("/")
@login_required
def index():
    account = current_account()
    user_row = query("SELECT * FROM users WHERE account_id=?", (account["id"],), one=True)
    menu_state = build_menu_view_model(account["id"], user_row["allergens"] if user_row else "")
    return render_template(
        "orders/index.html",
        account=account,
        user_row=user_row,
        menu=menu_state["menu"],
        state=menu_state,
        week_dates=get_week_dates(),
        current_menu_pdf_meta=get_current_menu_pdf_meta(),
        active_page="menu",
    )


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    account = current_account()
    if request.method == "POST":
        allergens = request.form.get("allergens", "")
        execute("UPDATE users SET allergens=? WHERE account_id=?", (allergens, account["id"]))
        return redirect(url_for("orders.profile"))
    user_row = query("SELECT * FROM users WHERE account_id=?", (account["id"],), one=True)
    rows = get_user_orders(account["id"])
    total_spend = sum(row["price_snapshot_cents"] for row in rows if row["status"] != "cancelled")
    unpaid = sum(row["price_snapshot_cents"] for row in rows if row["status"] in {"sent_to_vendor", "delivered", "invoiced"})
    return render_template(
        "orders/profile.html",
        account=account,
        user_row=user_row,
        rows=rows[:8],
        total_spend_text=f"{total_spend // 100} Kč",
        unpaid_text=f"{unpaid // 100} Kč",
        active_page="profile",
        password_change_required=bool(account['must_change_password']),
    )


@bp.route("/orders")
@login_required
def orders_report():
    account = current_account()
    rows = get_user_orders(account["id"])
    return render_template("orders/report.html", account=account, rows=rows, active_page="orders")


@bp.route("/order-api", methods=["POST"])
@login_required
def order_api():
    account = current_account()
    day = request.form.get("day", "")
    dish_id = int(request.form.get("dish_id", "0") or 0)
    try:
        state = place_order(account, day, dish_id)
        return jsonify(success=True, state=state, message="Dish selected.")
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400


@bp.route("/order-api/cancel", methods=["POST"])
@login_required
def order_api_cancel():
    account = current_account()
    day = request.form.get("day", "")
    try:
        state = cancel_order(account, day)
        return jsonify(success=True, state=state, message="Order cancelled.")
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400


@bp.route("/order-api/rate", methods=["POST"])
@login_required
def order_api_rate():
    account = current_account()
    dish_name = request.form.get("dish_name", "")
    if not dish_name:
        abort(400)
    rate_dish(account, dish_name)
    return jsonify(success=True, message="Rating stored.")
