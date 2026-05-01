from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..core.auth import current_account, require_role
from ..services.delivery import (
    grouped_today_summary,
    mark_today_delivered,
    set_delivery_event,
    today_delivery_rows,
)

bp = Blueprint("delivery", __name__, url_prefix="/admin/delivery")


@bp.route("/today")
@require_role("manager")
def today():
    rows = today_delivery_rows()
    return render_template(
        "delivery/today.html",
        account=current_account(),
        rows=rows,
        summary=grouped_today_summary(rows),
        active_page="admin",
    )


@bp.route("/today/received", methods=["POST"])
@require_role("manager")
def received():
    count = mark_today_delivered(current_account())
    flash(f"Obědy označeny jako doručené: {count}.")
    return redirect(url_for("delivery.today"))


@bp.route("/order/<int:order_id>/event", methods=["POST"])
@require_role("manager")
def order_event(order_id: int):
    event_type = request.form.get("event_type", "")
    note = request.form.get("note", "")
    try:
        set_delivery_event(current_account(), order_id, event_type, note)
        flash("Výdejový stav byl uložen.")
    except ValueError:
        flash("Neplatný výdejový stav.", "error")
    return redirect(url_for("delivery.today"))
