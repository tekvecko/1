from __future__ import annotations

from flask import has_request_context, session

from ..core.db import execute, query, log_event
from ..core.auth import account_full_name
from .notifications import sync_password_change_notification

ALLOWED_DAYS = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek"]

TRANSITIONS = {
    "draft": {"submitted", "locked", "cancelled"},
    "submitted": {"locked", "cancelled"},
    "locked": {"sent_to_vendor", "delivered", "cancelled"},
    "sent_to_vendor": {"delivered", "invoiced", "paid"},
    "delivered": {"handed_over", "invoiced", "paid"},
    "handed_over": {"paid"},
    "invoiced": {"paid"},
    "paid": set(),
    "cancelled": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def _active_restaurant_id() -> int:
    try:
        from ..restaurants.runtime import active_restaurant_id
        return active_restaurant_id()
    except Exception:
        return 1


def _day_sort_sql() -> str:
    return "CASE day WHEN 'Pondělí' THEN 1 WHEN 'Úterý' THEN 2 WHEN 'Středa' THEN 3 WHEN 'Čtvrtek' THEN 4 WHEN 'Pátek' THEN 5 ELSE 99 END"


def _emoji_for(name: str) -> str:
    n = (name or "").lower()
    if any(x in n for x in ["kuř", "řízek", "maso", "vepř", "hověz"]):
        return "🍖"
    if any(x in n for x in ["ryb", "losos", "tres"]):
        return "🐟"
    if any(x in n for x in ["salát", "zelen"]):
        return "🥗"
    if any(x in n for x in ["pizza"]):
        return "🍕"
    if any(x in n for x in ["polév", "vývar"]):
        return "🍲"
    if any(x in n for x in ["těst", "špag"]):
        return "🍝"
    return "🍽️"


def get_menu_by_day(restaurant_id: int | None = None):
    rid = restaurant_id or _active_restaurant_id()
    rows = query(
        f"SELECT * FROM menu WHERE restaurant_id=? ORDER BY {_day_sort_sql()}, id",
        (rid,),
    )

    grouped = {}
    for row in rows:
        grouped.setdefault(row["day"], []).append(dict(row))

    return grouped


def get_user_orders(account_id: int):
    return query(
        """
        SELECT
            o.*,
            COALESCE(m.day, o.day) AS menu_day,
            COALESCE(r.name, 'Výchozí restaurace') AS restaurant_name
        FROM orders o
        LEFT JOIN menu m ON m.id=o.dish_id
        LEFT JOIN restaurants r ON r.id=o.restaurant_id
        WHERE o.created_by_account_id=?
        ORDER BY o.created_at DESC, o.id DESC
        """,
        (account_id,),
    )


def _selected_orders(account_id: int, restaurant_id: int):
    rows = query(
        """
        SELECT day, dish_id
        FROM orders
        WHERE created_by_account_id=?
          AND restaurant_id=?
          AND status IN ('draft','submitted','locked','sent_to_vendor','delivered','handed_over','invoiced','paid')
        """,
        (account_id, restaurant_id),
    )
    return {row["day"]: row["dish_id"] for row in rows}


def _day_status(account_id: int, restaurant_id: int):
    rows = query(
        """
        SELECT day, status
        FROM orders
        WHERE created_by_account_id=? AND restaurant_id=?
        """,
        (account_id, restaurant_id),
    )
    out = {}
    for row in rows:
        if row["status"] != "cancelled":
            out[row["day"]] = "selected" if row["status"] == "draft" else row["status"]
    return out


def _popularity(restaurant_id: int):
    rows = query(
        """
        SELECT dish_id, COUNT(*) AS cnt
        FROM orders
        WHERE restaurant_id=?
          AND dish_id IS NOT NULL
          AND status NOT IN ('cancelled')
        GROUP BY dish_id
        """,
        (restaurant_id,),
    )
    return {row["dish_id"]: row["cnt"] for row in rows}


def _recent_names(account_id: int):
    rows = query(
        """
        SELECT dish_name_snapshot
        FROM orders
        WHERE created_by_account_id=?
          AND status NOT IN ('cancelled')
        ORDER BY created_at DESC
        LIMIT 30
        """,
        (account_id,),
    )
    return {row["dish_name_snapshot"] for row in rows}


def build_order_state(account_id: int, user_row=None):
    restaurant_id = _active_restaurant_id()
    menu = get_menu_by_day(restaurant_id)
    selected = _selected_orders(account_id, restaurant_id)
    statuses = _day_status(account_id, restaurant_id)
    pop = _popularity(restaurant_id)
    recent = _recent_names(account_id)

    allergens = ""
    if user_row and "allergens" in user_row.keys():
        allergens = (user_row["allergens"] or "").lower()

    cart_items = []
    for day, dishes in menu.items():
        for dish in dishes:
            d = dict(dish)
            dish_id = d["id"]
            selected_now = selected.get(day) == dish_id

            safe = True
            if allergens:
                safe = not any(part.strip() and part.strip() in d["dish_name"].lower() for part in allergens.split(","))

            d.update({
                "selected": selected_now,
                "safe": safe,
                "recommended": d["dish_name"] in recent,
                "emoji": _emoji_for(d["dish_name"]),
                "popularity": pop.get(dish_id, 0),
                "thumbs": pop.get(dish_id, 0),
                "rated": False,
            })

            if selected_now:
                cart_items.append({
                    "day": day,
                    "dish_id": dish_id,
                    "dish_name": d["dish_name"],
                    "price_text": d["price_text"],
                    "price_cents": d["price_cents"],
                    "emoji": d["emoji"],
                    "restaurant_id": restaurant_id,
                })

            dish.clear()
            dish.update(d)

    cart_total = sum(int(item.get("price_cents") or 0) for item in cart_items)

    return {
        "menu": menu,
        "menu_days": list(menu.keys()) or ALLOWED_DAYS,
        "cart_items": cart_items,
        "cart_count": len(cart_items),
        "cart_total_cents": cart_total,
        "cart_total_text": f"{cart_total // 100} Kč",
        "day_status_by_day": statuses,
        "restaurant_id": restaurant_id,
    }


def place_order(account, day: str, dish_id: int):
    restaurant_id = _active_restaurant_id()
    dish = query(
        "SELECT * FROM menu WHERE id=? AND restaurant_id=?",
        (dish_id, restaurant_id),
        one=True,
    )

    if not dish:
        return {"success": False, "message": "Jídlo nebylo nalezeno pro vybranou restauraci."}

    day = day or dish["day"]
    if day != dish["day"]:
        raise ValueError("You can choose only one lunch for the selected day.")

    existing = query(
        """
        SELECT *
        FROM orders
        WHERE created_by_account_id=?
          AND restaurant_id=?
          AND day=?
          AND status NOT IN ('cancelled')
        """,
        (account["id"], restaurant_id, day),
        one=True,
    )

    if existing:
        execute(
            """
            UPDATE orders
            SET dish_id=?,
                status='draft',
                dish_name_snapshot=?,
                price_snapshot_text=?,
                price_snapshot_cents=?,
                cancelled_at=NULL
            WHERE id=?
            """,
            (dish["id"], dish["dish_name"], dish["price_text"], dish["price_cents"], existing["id"]),
        )
    else:
        execute(
            """
            INSERT INTO orders(
                created_by_account_id,
                restaurant_id,
                day,
                dish_id,
                status,
                dish_name_snapshot,
                price_snapshot_text,
                price_snapshot_cents
            )
            VALUES (?, ?, ?, ?, 'draft', ?, ?, ?)
            """,
            (
                account["id"],
                restaurant_id,
                day,
                dish["id"],
                dish["dish_name"],
                dish["price_text"],
                dish["price_cents"],
            ),
        )

    log_event(
        "order_selected",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        detail=f"restaurant_id={restaurant_id}; day={day}; dish_id={dish_id}",
    )

    return {
        "success": True,
        "message": "Jídlo bylo vybráno.",
        "state": build_order_state(account["id"]),
    }


def cancel_order(account, day: str):
    restaurant_id = _active_restaurant_id()
    order = query(
        """
        SELECT *
        FROM orders
        WHERE created_by_account_id=?
          AND restaurant_id=?
          AND day=?
          AND status NOT IN ('cancelled')
        """,
        (account["id"], restaurant_id, day),
        one=True,
    )

    if not order:
        return {"success": False, "message": "Objednávka nebyla nalezena."}

    execute(
        "UPDATE orders SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP WHERE id=?",
        (order["id"],),
    )

    log_event(
        "order_cancelled",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        detail=f"restaurant_id={restaurant_id}; day={day}",
    )

    return {
        "success": True,
        "message": "Objednávka byla zrušena.",
        "state": build_order_state(account["id"]),
    }


def rate_dish(account, dish_name: str):
    log_event(
        "dish_rated",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        detail=dish_name,
    )
    return {"success": True, "message": "Hodnocení uloženo."}

# Backward compatibility for existing routes.py
def build_menu_view_model(account_id: int, user_row=None):
    return build_order_state(account_id, user_row)

# === Compatibility aliases for old routes/templates ===
def current_state(account_id: int, user_row=None):
    return build_order_state(account_id, user_row)

def build_menu_view_model(account_id: int, user_row=None):
    return build_order_state(account_id, user_row)

def select_order(account, day: str, dish_id: int):
    return place_order(account, day, int(dish_id))

def submit_order(account, day: str, dish_id: int):
    return place_order(account, day, int(dish_id))
