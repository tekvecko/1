from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from ..core.auth import current_account, require_role
from ..core.db import account_full_name, execute, query
from ..core.utils import extract_price_cents, format_price_czk, full_name_from_parts, normalize_email, normalize_person_name
from ..services.billing import get_lock_state
from ..services.notifications import create_notification, sync_password_change_notification
from ..services.imports import (
    get_current_menu_pdf_meta,
    list_menu_weeks,
    active_menu_week,
    selected_menu_week_id,
    selected_menu_week,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("")
@require_role("manager")
def dashboard():
    account = current_account()
    selected_week_id = selected_menu_week_id()
    selected_week_id = selected_menu_week_id()
    menu_rows = query("SELECT * FROM menu WHERE week_id=? ORDER BY CASE day WHEN 'Pondělí' THEN 1 WHEN 'Úterý' THEN 2 WHEN 'Středa' THEN 3 WHEN 'Čtvrtek' THEN 4 WHEN 'Pátek' THEN 5 ELSE 99 END, id", (selected_week_id,))
    audit_rows = query("SELECT * FROM audit_log ORDER BY id DESC LIMIT 25")
    order_rows = query(
        """
        SELECT o.*, a.first_name, a.last_name, a.email
        FROM orders o
        JOIN accounts a ON a.id=o.created_by_account_id
        ORDER BY o.created_at DESC LIMIT 50
        """
    )
    debtors = query(
        """
        SELECT
            a.id,
            a.first_name,
            a.last_name,
            a.email,
            SUM(o.price_snapshot_cents) AS total_cents,
            SUM(COALESCE(o.paid_amount_cents, 0)) AS paid_cents,
            SUM(o.price_snapshot_cents - COALESCE(o.paid_amount_cents, 0)) AS cents,
            COUNT(*) AS item_count,
            GROUP_CONCAT(DISTINCT o.payment_status) AS payment_states
        FROM orders o
        JOIN accounts a ON a.id=o.created_by_account_id
        WHERE o.status != 'cancelled'
          AND o.payment_status IN ('unpaid', 'partial', '')
          AND (o.price_snapshot_cents - COALESCE(o.paid_amount_cents, 0)) > 0
        GROUP BY a.id, a.first_name, a.last_name, a.email
        ORDER BY cents DESC, a.last_name, a.first_name
        """
    )
    return render_template(
        'admin/dashboard.html',
        account=account,
        menu_rows=menu_rows,
        menu_count=len(menu_rows),
        accounts=query('SELECT * FROM accounts ORDER BY role DESC, last_name, first_name, email'),
        orders=order_rows,
        debtors=debtors,
        audit_rows=audit_rows,
        lock_state=get_lock_state(),
        current_menu_pdf_meta=get_current_menu_pdf_meta(),
        menu_weeks=list_menu_weeks(),
        active_menu_week=active_menu_week(),
        selected_week_id=selected_week_id,
        active_page='admin',
    )


@bp.route('/menu/add', methods=['POST'])
@require_role('manager')
def add_menu_item():
    day = request.form.get('day', '')
    dish_name = request.form.get('dish_name', '')
    price_text = request.form.get('price_text', '')
    price_cents = extract_price_cents(price_text)
    execute(
        'INSERT INTO menu(day, dish_name, price_text, price_cents, week_id) VALUES (?, ?, ?, ?, ?)',
        (day, dish_name, format_price_czk(price_cents), price_cents, int(request.form.get('week_id') or selected_menu_week_id())),
    )
    flash('Menu item added.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/menu/delete/<int:dish_id>', methods=['POST'])
@require_role('manager')
def delete_menu_item(dish_id: int):
    execute('DELETE FROM menu WHERE id=?', (dish_id,))
    flash('Menu item deleted.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/accounts/create', methods=['POST'])
@require_role('super_admin')
def create_account():
    first_name = normalize_person_name(request.form.get('first_name', ''))
    last_name = normalize_person_name(request.form.get('last_name', ''))
    email = normalize_email(request.form.get('email', ''))
    role = request.form.get('role', 'user')
    password = request.form.get('password', '') or 'heslo123'
    if not first_name or not last_name or not email:
        flash('Vyplňte křestní jméno, příjmení a e-mail.', 'error')
        return redirect(url_for('admin.dashboard'))
    display_name = full_name_from_parts(first_name, last_name)
    cur = execute(
        "INSERT INTO accounts(username, display_name, first_name, last_name, email, password_hash, must_change_password, role, is_active) VALUES (?, ?, ?, ?, ?, ?, 1, ?, 1)",
        (email, display_name, first_name, last_name, email, generate_password_hash(password), role),
    )
    execute('INSERT OR IGNORE INTO users(account_id, allergens) VALUES(?, "")', (cur.lastrowid,))
    create_notification(cur.lastrowid, 'Změňte výchozí heslo', 'Účet byl vytvořen s dočasným heslem. Změňte ho při prvním přihlášení.', link_url='/profile#password-change', level='warning', kind='security', dedupe_key='password_change_required')
    flash('Účet byl vytvořen.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/accounts/<int:account_id>/update', methods=['POST'])
@require_role('super_admin')
def update_account(account_id: int):
    first_name = normalize_person_name(request.form.get('first_name', ''))
    last_name = normalize_person_name(request.form.get('last_name', ''))
    email = normalize_email(request.form.get('email', ''))
    role = request.form.get('role', 'user')
    is_active = 1 if request.form.get('is_active') == '1' else 0
    display_name = full_name_from_parts(first_name, last_name)
    execute(
        'UPDATE accounts SET first_name=?, last_name=?, display_name=?, email=?, username=?, role=?, is_active=? WHERE id=?',
        (first_name, last_name, display_name, email, email if account_id != 1 else 'admin', role, is_active, account_id),
    )
    if account_id == current_account()['id'] and not is_active:
        flash('Aktuálně přihlášený účet nelze deaktivovat.', 'error')
        execute('UPDATE accounts SET is_active=1 WHERE id=?', (account_id,))
    flash('Účet byl upraven.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/accounts/<int:account_id>/role', methods=['POST'])
@require_role('super_admin')
def update_role(account_id: int):
    role = request.form.get('role', 'user')
    execute('UPDATE accounts SET role=? WHERE id=?', (role, account_id))
    flash('Role updated.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/accounts/<int:account_id>/reset-password', methods=['POST'])
@require_role('super_admin')
def reset_account_password(account_id: int):
    new_password = request.form.get('new_password', '') or 'heslo123'
    execute('UPDATE accounts SET password_hash=?, must_change_password=1 WHERE id=?', (generate_password_hash(new_password), account_id))
    acct = query('SELECT * FROM accounts WHERE id=?', (account_id,), one=True)
    if acct:
        sync_password_change_notification(acct)
    flash('Heslo bylo resetováno.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/accounts/<int:account_id>/delete', methods=['POST'])
@require_role('super_admin')
def delete_account(account_id: int):
    acct = query('SELECT * FROM accounts WHERE id=?', (account_id,), one=True)
    me = current_account()
    if not acct:
        flash('Účet nebyl nalezen.', 'error')
    elif acct['username'] == 'admin':
        flash('Bootstrap admin účet nelze smazat.', 'error')
    elif acct['id'] == me['id']:
        flash('Nelze smazat právě přihlášený účet.', 'error')
    else:
        execute('DELETE FROM accounts WHERE id=?', (account_id,))
        flash('Účet byl smazán.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/reset-week', methods=['POST'])
@require_role('super_admin')
def reset_week():
    execute('DELETE FROM orders')
    flash('All orders reset.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/export/json')
@require_role('billing_admin')
def export_json():
    rows = [dict(row) for row in query('SELECT * FROM orders ORDER BY created_at DESC')]
    return jsonify(rows)


# ============================================================
# Production CSV exports
# ============================================================

def _csv_export_guard():
    from flask import abort
    from ..core.auth import current_account

    account = current_account()
    if not account or account["role"] not in {"admin", "super_admin"}:
        abort(403)
    return account


def _row_value(row, key, default=""):
    try:
        value = row[key]
    except Exception:
        value = default
    return "" if value is None else value


def _csv_response(filename, headers, rows):
    import csv
    from io import StringIO
    from flask import Response

    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)

    for row in rows:
        writer.writerow([_row_value(row, h) for h in headers])

    data = out.getvalue()
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
        },
    )


@bp.route("/export/orders.csv")
def export_orders_csv():
    _csv_export_guard()

    rows = query("""
        SELECT
            o.id,
            o.created_at,
            o.finalized_at,
            o.day,
            o.status,
            o.payment_status,
            o.paid_amount_cents,
            o.price_snapshot_cents,
            o.dish_name_snapshot,
            o.price_snapshot_text,
            o.note,
            o.payment_note,
            o.restaurant_id,
            COALESCE(r.name, '') AS restaurant_name,
            a.id AS account_id,
            a.username,
            a.email,
            a.first_name,
            a.last_name,
            a.display_name,
            a.role
        FROM orders o
        LEFT JOIN accounts a ON a.id = o.created_by_account_id
        LEFT JOIN restaurants r ON r.id = o.restaurant_id
        ORDER BY o.created_at DESC, o.id DESC
    """)

    headers = [
        "id",
        "created_at",
        "finalized_at",
        "day",
        "status",
        "payment_status",
        "paid_amount_cents",
        "price_snapshot_cents",
        "dish_name_snapshot",
        "price_snapshot_text",
        "note",
        "payment_note",
        "restaurant_id",
        "restaurant_name",
        "account_id",
        "username",
        "email",
        "first_name",
        "last_name",
        "display_name",
        "role",
    ]

    return _csv_response("orders.csv", headers, rows)


@bp.route("/export/billing.csv")
def export_billing_csv():
    _csv_export_guard()

    rows = query("""
        SELECT
            a.id AS account_id,
            a.username,
            a.email,
            a.first_name,
            a.last_name,
            a.display_name,
            COALESCE(r.name, '') AS restaurant_name,
            o.restaurant_id,
            COUNT(o.id) AS orders_count,
            COALESCE(SUM(o.price_snapshot_cents), 0) AS total_cents,
            COALESCE(SUM(o.paid_amount_cents), 0) AS paid_cents,
            COALESCE(SUM(o.price_snapshot_cents - o.paid_amount_cents), 0) AS remaining_cents
        FROM orders o
        LEFT JOIN accounts a ON a.id = o.created_by_account_id
        LEFT JOIN restaurants r ON r.id = o.restaurant_id
        WHERE o.status NOT IN ('cancelled')
        GROUP BY
            a.id,
            a.username,
            a.email,
            a.first_name,
            a.last_name,
            a.display_name,
            r.name,
            o.restaurant_id
        ORDER BY remaining_cents DESC, total_cents DESC, a.last_name, a.first_name
    """)

    headers = [
        "account_id",
        "username",
        "email",
        "first_name",
        "last_name",
        "display_name",
        "restaurant_name",
        "restaurant_id",
        "orders_count",
        "total_cents",
        "paid_cents",
        "remaining_cents",
    ]

    return _csv_response("billing.csv", headers, rows)


@bp.route("/export/users.csv")
def export_users_csv():
    _csv_export_guard()

    rows = query("""
        SELECT
            a.id,
            a.username,
            a.email,
            a.first_name,
            a.last_name,
            a.display_name,
            a.role,
            a.is_active,
            a.must_change_password,
            a.created_at,
            a.last_login_at,
            COALESCE(u.allergens, '') AS allergens
        FROM accounts a
        LEFT JOIN users u ON u.account_id = a.id
        ORDER BY a.role DESC, a.last_name, a.first_name, a.username
    """)

    headers = [
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "display_name",
        "role",
        "is_active",
        "must_change_password",
        "created_at",
        "last_login_at",
        "allergens",
    ]

    return _csv_response("users.csv", headers, rows)


@bp.route("/export/menu.csv")
def export_menu_csv():
    _csv_export_guard()

    rows = query("""
        SELECT
            m.id,
            m.day,
            m.dish_name,
            m.price_text,
            m.price_cents,
            m.image_url,
            m.created_at,
            m.restaurant_id,
            COALESCE(r.name, '') AS restaurant_name
        FROM menu m
        LEFT JOIN restaurants r ON r.id = m.restaurant_id
        ORDER BY r.name, m.day, m.id
    """)

    headers = [
        "id",
        "day",
        "dish_name",
        "price_text",
        "price_cents",
        "image_url",
        "created_at",
        "restaurant_id",
        "restaurant_name",
    ]

    return _csv_response("menu.csv", headers, rows)


@bp.route('/weeks/<int:week_id>/activate', methods=['POST'])
@require_role('manager')
def activate_week_admin_route(week_id: int):
    from ..services.imports import activate_menu_week
    week = activate_menu_week(week_id)
    if week:
        flash(f"Aktivní týden: {week['label']}")
    else:
        flash("Týden nebyl nalezen.", "error")
    return redirect(url_for('admin.dashboard'))


@bp.route('/weeks/<int:week_id>/status', methods=['POST'])
@require_role('manager')
def update_week_status_admin_route(week_id: int):
    from ..services.imports import update_menu_week_status
    week = update_menu_week_status(week_id, request.form.get('status', 'open'))
    if week:
        flash(f"Stav týdne uložen: {week['label']} / {week['status']}")
    else:
        flash("Týden nebyl nalezen.", "error")
    return redirect(url_for('admin.dashboard'))


@bp.route('/weeks/create', methods=['POST'])
@require_role('manager')
def create_week_admin_route():
    from ..services.imports import create_menu_week
    week = create_menu_week(
        label=request.form.get('label', ''),
        week_start=request.form.get('week_start', ''),
        week_end=request.form.get('week_end', ''),
        status=request.form.get('status', 'open'),
        activate=request.form.get('activate') == '1',
    )
    flash(f"Týden vytvořen: {week['label']}")
    return redirect(url_for('admin.dashboard'))
