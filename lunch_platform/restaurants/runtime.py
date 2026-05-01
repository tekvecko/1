from __future__ import annotations

import re
import sqlite3
from flask import abort, current_app, has_request_context, jsonify, redirect, render_template_string, request, session, url_for

from ..core.auth import current_account
from ..core.db import execute, query


def _columns(table: str) -> set[str]:
    rows = query(f"PRAGMA table_info({table})")
    return {row["name"] for row in rows}


def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9á-ž]+", "-", value, flags=re.I).strip("-")
    return value or "restaurace"


def ensure_multi_restaurant_schema(app=None) -> None:
    execute("""
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
        )
    """)

    existing = query("SELECT * FROM restaurants ORDER BY id LIMIT 1", one=True)
    if not existing:
        execute(
            "INSERT INTO restaurants(name, slug, description, sort_order) VALUES (?, ?, ?, ?)",
            ("Výchozí restaurace", "default", "Původní menu", 1),
        )

    menu_cols = _columns("menu")
    if "restaurant_id" not in menu_cols:
        execute("ALTER TABLE menu ADD COLUMN restaurant_id INTEGER NOT NULL DEFAULT 1")

    order_cols = _columns("orders")
    if "restaurant_id" not in order_cols:
        execute("ALTER TABLE orders ADD COLUMN restaurant_id INTEGER NOT NULL DEFAULT 1")

    execute("UPDATE menu SET restaurant_id=1 WHERE restaurant_id IS NULL OR restaurant_id=''")
    execute("UPDATE orders SET restaurant_id=1 WHERE restaurant_id IS NULL OR restaurant_id=''")

    execute("CREATE INDEX IF NOT EXISTS idx_menu_restaurant_day ON menu(restaurant_id, day, id)")
    execute("CREATE INDEX IF NOT EXISTS idx_orders_restaurant_account_day ON orders(restaurant_id, created_by_account_id, day)")


def list_restaurants(active_only: bool = True):
    if active_only:
        return query("SELECT * FROM restaurants WHERE is_active=1 ORDER BY sort_order, name, id")
    return query("SELECT * FROM restaurants ORDER BY is_active DESC, sort_order, name, id")


def get_restaurant(restaurant_id: int):
    return query("SELECT * FROM restaurants WHERE id=?", (restaurant_id,), one=True)


def active_restaurant_id() -> int:
    if has_request_context():
        rid = session.get("restaurant_id")
        if rid:
            row = get_restaurant(int(rid))
            if row and row["is_active"]:
                return int(row["id"])

    row = query("SELECT id FROM restaurants WHERE is_active=1 ORDER BY sort_order, id LIMIT 1", one=True)
    return int(row["id"]) if row else 1


def set_active_restaurant(restaurant_id: int) -> bool:
    row = get_restaurant(int(restaurant_id))
    if not row or not row["is_active"]:
        return False
    session["restaurant_id"] = int(row["id"])
    return True


def create_restaurant(name: str, description: str = "", phone: str = "", email: str = ""):
    name = (name or "").strip()
    if not name:
        raise ValueError("Název restaurace je povinný.")

    base = _slugify(name)
    slug = base
    i = 2
    while query("SELECT id FROM restaurants WHERE slug=?", (slug,), one=True):
        slug = f"{base}-{i}"
        i += 1

    cur = execute(
        "INSERT INTO restaurants(name, slug, description, phone, email, sort_order, is_active) VALUES (?, ?, ?, ?, ?, 100, 1)",
        (name, slug, description.strip(), phone.strip(), email.strip()),
    )
    return get_restaurant(cur.lastrowid)


def _is_manager(account) -> bool:
    return bool(account and account["role"] in {"manager", "admin", "super_admin"})


def init_restaurants(app) -> None:
    with app.app_context():
        ensure_multi_restaurant_schema(app)

    @app.context_processor
    def _inject_restaurants():
        try:
            restaurants = list_restaurants(True)
            rid = active_restaurant_id()
            active = get_restaurant(rid)
        except Exception:
            restaurants, rid, active = [], 1, None

        return {
            "all_restaurants": restaurants,
            "active_restaurant_id": rid,
            "active_restaurant": active,
        }

    @app.post("/restaurant/select")
    def _select_restaurant():
        payload = request.get_json(silent=True) or request.form
        rid = payload.get("restaurant_id") or payload.get("id")
        if not rid or not set_active_restaurant(int(rid)):
            return jsonify({"success": False, "message": "Restaurace nebyla nalezena."}), 404
        return jsonify({"success": True, "restaurant_id": int(rid)})

    @app.route("/admin/restaurants", methods=["GET", "POST"])
    def _admin_restaurants():
        account = current_account()
        if not _is_manager(account):
            abort(403)

        if request.method == "POST":
            name = request.form.get("name", "")
            description = request.form.get("description", "")
            phone = request.form.get("phone", "")
            email = request.form.get("email", "")
            try:
                create_restaurant(name, description, phone, email)
            except Exception as exc:
                return f"Nelze přidat restauraci: {exc}", 400
            return redirect(url_for("_admin_restaurants"))

        rows = list_restaurants(False)
        return render_template_string("""
{% extends 'base.html' %}
{% block title %}Restaurace · FINAL Lunch{% endblock %}
{% block content %}
<section class="card pad-lg stack">
  <div class="section-title">
    <h1 class="display" style="color:#fff;margin:0">Restaurace</h1>
    <p class="muted">Správa více restaurací pro objednávání obědů.</p>
  </div>

  <form method="post" class="stack" style="display:grid;gap:12px">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <input class="search-input" name="name" placeholder="Název restaurace" required>
    <input class="search-input" name="description" placeholder="Popis">
    <input class="search-input" name="phone" placeholder="Telefon">
    <input class="search-input" name="email" placeholder="E-mail">
    <button class="btn-blue label" type="submit">Přidat restauraci</button>
  </form>
</section>

<section class="card pad-lg stack" style="margin-top:16px">
  {% for r in rows %}
    <div class="kpi">
      <div>
        <strong style="color:#fff">{{ r.name }}</strong>
        <div class="muted small">{{ r.description or 'bez popisu' }} · {{ 'aktivní' if r.is_active else 'vypnutá' }}</div>
      </div>
    </div>
  {% endfor %}
</section>
{% endblock %}
""", rows=rows, active_page="admin")
