from __future__ import annotations

from flask import Blueprint, flash, redirect, request, url_for

from ..core.auth import current_account, require_role
from ..services.billing import lock_submitted_orders, mark_user_paid, pay_all, set_lock_state

bp = Blueprint("billing", __name__, url_prefix="/admin/billing")


@bp.route("/lock-state", methods=["POST"])
@require_role("billing_admin")
def update_lock_state():
    set_lock_state(current_account(), request.form.get("state", "auto"))
    flash("Lock state updated.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/lock-week", methods=["POST"])
@require_role("billing_admin")
def lock_week():
    count = lock_submitted_orders(current_account())
    flash(f"Locked {count} orders.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/mark-paid", methods=["POST"])
@require_role("billing_admin")
def mark_paid():
    target_account_id = int(request.form.get("target_account_id", "0"))
    count = mark_user_paid(current_account(), target_account_id)
    flash(f"Marked {count} orders paid.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/pay-all", methods=["POST"])
@require_role("billing_admin")
def pay_everyone():
    count = pay_all(current_account())
    flash(f"Marked {count} orders paid.")
    return redirect(url_for("admin.dashboard"))
