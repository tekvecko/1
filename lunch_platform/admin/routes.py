from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from ..core.auth import current_account, require_role
from ..core.db import account_full_name, execute, query
from ..core.utils import extract_price_cents, format_price_czk, full_name_from_parts, normalize_email, normalize_person_name, normalize_spaces
from ..services.billing import get_lock_state
from ..services.imports import get_current_menu_pdf_meta
from ..services.notifications import create_notification, sync_password_change_notification

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("")
@require_role("manager")
def dashboard():
    account = current_account()
    menu_rows = query("SELECT * FROM menu ORDER BY CASE day WHEN 'Pondělí' THEN 1 WHEN 'Úterý' THEN 2 WHEN 'Středa' THEN 3 WHEN 'Čtvrtek' THEN 4 WHEN 'Pátek' THEN 5 ELSE 99 END, id")
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
        SELECT a.id, a.first_name, a.last_name, a.email, SUM(o.price_snapshot_cents) AS cents, COUNT(*) AS item_count
        FROM orders o
        JOIN accounts a ON a.id=o.created_by_account_id
        WHERE o.status IN ('sent_to_vendor','delivered','invoiced')
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
        'INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES (?, ?, ?, ?)',
        (day, dish_name, format_price_czk(price_cents), price_cents),
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
    username = normalize_spaces(request.form.get('username', ''))
    first_name = normalize_person_name(request.form.get('first_name', ''))
    last_name = normalize_person_name(request.form.get('last_name', ''))
    email = normalize_email(request.form.get('email', ''))
    role = request.form.get('role', 'user')
    password = request.form.get('password', '') or 'heslo123'
    password_confirm = request.form.get('password_confirm', '') or password
    if not username:
        username = email
    if not first_name or not last_name or not email:
        flash('Vyplňte křestní jméno, příjmení a e-mail.', 'error')
        return redirect(url_for('admin.dashboard'))
    if password != password_confirm:
        flash('Hesla se neshodují.', 'error')
        return redirect(url_for('admin.dashboard'))
    display_name = full_name_from_parts(first_name, last_name)
    cur = execute(
        "INSERT INTO accounts(username, display_name, first_name, last_name, email, password_hash, must_change_password, role, is_active) VALUES (?, ?, ?, ?, ?, ?, 1, ?, 1)",
        (username, display_name, first_name, last_name, email, generate_password_hash(password), role),
    )
    execute('INSERT OR IGNORE INTO users(account_id, allergens) VALUES(?, "")', (cur.lastrowid,))
    create_notification(cur.lastrowid, 'Změňte výchozí heslo', 'Účet byl vytvořen s dočasným heslem. Změňte ho při prvním přihlášení.', link_url='/profile#password-change', level='warning', kind='security', dedupe_key='password_change_required')
    flash('Účet byl vytvořen.')
    return redirect(url_for('admin.dashboard'))


@bp.route('/accounts/<int:account_id>/update', methods=['POST'])
@bp.route('/accounts/<int:account_id>/profile', methods=['POST'])
@require_role('super_admin')
def update_account(account_id: int):
    acct = query('SELECT * FROM accounts WHERE id=?', (account_id,), one=True)
    if not acct:
        flash('Účet nebyl nalezen.', 'error')
        return redirect(url_for('admin.dashboard'))

    first_name = normalize_person_name(request.form.get('first_name', ''))
    last_name = normalize_person_name(request.form.get('last_name', ''))
    email = normalize_email(request.form.get('email', ''))
    role = request.form.get('role', acct['role'])
    display_name = full_name_from_parts(first_name, last_name)

    if request.form.get('is_active') is None:
        is_active = acct['is_active']
    else:
        is_active = 1 if request.form.get('is_active') == '1' else 0

    username = acct['username']
    if account_id != 1:
        username = normalize_spaces(request.form.get('username', '')) or acct['username']

    execute(
        'UPDATE accounts SET first_name=?, last_name=?, display_name=?, email=?, username=?, role=?, is_active=? WHERE id=?',
        (first_name, last_name, display_name, email, username, role, is_active, account_id),
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
