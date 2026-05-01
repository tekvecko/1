from __future__ import annotations

from ..core.db import account_full_name, execute, log_event, query


def ensure_delivery_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            note TEXT DEFAULT '',
            actor_account_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def today_delivery_rows():
    ensure_delivery_schema()
    return query(
        """
        SELECT
            o.*,
            a.first_name,
            a.last_name,
            a.email,
            COALESCE(m.dish_name, 'Neznámé jídlo') AS delivery_dish_name,
            COALESCE(m.price_text, printf('%.0f Kč', COALESCE(o.price_snapshot_cents, m.price_cents, 0) / 100.0)) AS delivery_price_text,
            (
                SELECT de.event_type
                FROM delivery_events de
                WHERE de.order_id=o.id
                ORDER BY de.id DESC
                LIMIT 1
            ) AS delivery_state
        FROM orders o
        JOIN accounts a ON a.id=o.created_by_account_id
        LEFT JOIN menu m ON m.id=o.dish_id
        WHERE o.day = CASE strftime('%w','now','localtime')
            WHEN '1' THEN 'Pondělí'
            WHEN '2' THEN 'Úterý'
            WHEN '3' THEN 'Středa'
            WHEN '4' THEN 'Čtvrtek'
            WHEN '5' THEN 'Pátek'
            ELSE o.day
        END
        AND o.status IN ('locked','sent_to_vendor','delivered','handed_over','invoiced','submitted')
        ORDER BY delivery_dish_name, a.last_name, a.first_name, o.id
        """
    )


def grouped_today_summary(rows):
    groups = {}
    for row in rows:
        dish = row["delivery_dish_name"]
        groups.setdefault(
            dish,
            {
                "dish_name": dish,
                "count": 0,
                "price_text": row["delivery_price_text"],
            },
        )
        groups[dish]["count"] += 1
    return sorted(groups.values(), key=lambda x: x["dish_name"].lower())


def mark_today_delivered(account) -> int:
    ensure_delivery_schema()
    rows = today_delivery_rows()
    count = 0

    for row in rows:
        if row["status"] in ("locked", "sent_to_vendor", "submitted"):
            execute("UPDATE orders SET status='delivered' WHERE id=?", (row["id"],))
            count += 1

    log_event(
        "delivery_received",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        detail=f"count={count}",
    )
    return count


def set_delivery_event(account, order_id: int, event_type: str, note: str = "") -> None:
    ensure_delivery_schema()

    if event_type not in {"handed_over", "issue", "not_picked_up"}:
        raise ValueError("Invalid delivery event")

    execute(
        """
        INSERT INTO delivery_events(order_id, event_type, note, actor_account_id)
        VALUES (?, ?, ?, ?)
        """,
        (order_id, event_type, note.strip(), account["id"]),
    )

    if event_type == "handed_over":
        execute("UPDATE orders SET status='handed_over' WHERE id=?", (order_id,))
    elif event_type in {"issue", "not_picked_up"}:
        execute("UPDATE orders SET status='delivered' WHERE id=?", (order_id,))

    log_event(
        f"delivery_{event_type}",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        detail=f"order_id={order_id}",
    )
