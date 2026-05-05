from __future__ import annotations

from ..core.db import execute, get_setting, log_event, query, set_setting, account_full_name
from .orders import can_transition


def get_lock_state() -> str:
    return get_setting("lock_state", "auto")


def set_lock_state(account, state: str) -> None:
    if state not in {"auto", "locked", "unlocked"}:
        raise ValueError("Unsupported lock state")
    set_setting("lock_state", state)
    log_event("lock_state_changed", account_id=account["id"], actor=account_full_name(account), role=account["role"], detail=state)


def lock_submitted_orders(account) -> int:
    rows = query("SELECT id, status FROM orders WHERE status IN ('draft', 'submitted')")
    count = 0
    for row in rows:
        new_state = "locked"
        if can_transition(row["status"], new_state):
            execute("UPDATE orders SET status='locked', locked_at=CURRENT_TIMESTAMP, finalized_at=COALESCE(finalized_at, CURRENT_TIMESTAMP) WHERE id=?", (row["id"],))
            count += 1
    log_event("orders_locked", account_id=account["id"], actor=account_full_name(account), role=account["role"], detail=f"count={count}")
    return count


def mark_user_paid(account, target_account_id: int) -> int:
    rows = query("SELECT id FROM orders WHERE created_by_account_id=? AND status IN ('sent_to_vendor', 'delivered', 'invoiced')", (target_account_id,))
    for row in rows:
        execute("UPDATE orders SET status='paid', paid_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
    log_event("billing_mark_paid", account_id=account["id"], actor=account_full_name(account), role=account["role"], target=str(target_account_id), detail=f"count={len(rows)}")
    return len(rows)


def pay_all(account) -> int:
    rows = query("SELECT id FROM orders WHERE status IN ('sent_to_vendor', 'delivered', 'invoiced')")
    for row in rows:
        execute("UPDATE orders SET status='paid', paid_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
    log_event("billing_pay_all", account_id=account["id"], actor=account_full_name(account), role=account["role"], detail=f"count={len(rows)}")
    return len(rows)

# PAYMENT FLOW V2 OVERRIDES
def _parse_amount_cents(value: str) -> int:
    import re

    raw = (value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0

    match = re.search(r"(\d+(?:\.\d{1,2})?)", raw)
    if not match:
        return 0

    amount = float(match.group(1))
    return int(round(amount * 100))


def _open_payment_orders(target_account_id: int):
    return query(
        """
        SELECT *
        FROM orders
        WHERE created_by_account_id=?
          AND status != 'cancelled'
          AND payment_status IN ('unpaid', 'partial', '')
        ORDER BY
          CASE day WHEN 'Pondělí' THEN 1 WHEN 'Úterý' THEN 2 WHEN 'Středa' THEN 3 WHEN 'Čtvrtek' THEN 4 WHEN 'Pátek' THEN 5 ELSE 99 END,
          id
        """,
        (target_account_id,),
    )


def mark_user_paid(account, target_account_id: int) -> int:
    rows = _open_payment_orders(target_account_id)

    for row in rows:
        execute(
            """
            UPDATE orders
            SET payment_status='paid',
                paid_amount_cents=price_snapshot_cents,
                status='paid',
                paid_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (row["id"],),
        )

    log_event(
        "billing_user_paid_all",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        target=str(target_account_id),
        detail=f"count={len(rows)}",
    )

    return len(rows)


def mark_user_amount(account, target_account_id: int, amount_text: str) -> dict:
    amount_cents = _parse_amount_cents(amount_text)
    if amount_cents <= 0:
        raise ValueError("Zadej částku větší než 0 Kč.")

    remaining = amount_cents
    touched = 0

    for row in _open_payment_orders(target_account_id):
        if remaining <= 0:
            break

        price = int(row["price_snapshot_cents"] or 0)
        already_paid = int(row["paid_amount_cents"] or 0)
        due = max(0, price - already_paid)

        if due <= 0:
            execute(
                """
                UPDATE orders
                SET payment_status='paid',
                    paid_amount_cents=price_snapshot_cents,
                    status='paid',
                    paid_at=COALESCE(paid_at, CURRENT_TIMESTAMP)
                WHERE id=?
                """,
                (row["id"],),
            )
            continue

        add = min(due, remaining)
        new_paid = already_paid + add
        remaining -= add
        touched += 1

        if new_paid >= price:
            execute(
                """
                UPDATE orders
                SET paid_amount_cents=?,
                    payment_status='paid',
                    status='paid',
                    paid_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (new_paid, row["id"]),
            )
        else:
            execute(
                """
                UPDATE orders
                SET paid_amount_cents=?,
                    payment_status='partial',
                    payment_note=?
                WHERE id=?
                """,
                (new_paid, f"Částečně zaplaceno: {new_paid // 100} Kč", row["id"]),
            )

    log_event(
        "billing_user_paid_amount",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        target=str(target_account_id),
        detail=f"amount_cents={amount_cents}; touched={touched}; rest={remaining}",
    )

    return {
        "amount_cents": amount_cents,
        "used_cents": amount_cents - remaining,
        "remaining_cents": remaining,
        "touched": touched,
    }


def pay_all(account) -> int:
    rows = query(
        """
        SELECT id
        FROM orders
        WHERE status != 'cancelled'
          AND payment_status IN ('unpaid', 'partial', '')
        """
    )

    for row in rows:
        execute(
            """
            UPDATE orders
            SET payment_status='paid',
                paid_amount_cents=price_snapshot_cents,
                status='paid',
                paid_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (row["id"],),
        )

    log_event(
        "billing_pay_all",
        account_id=account["id"],
        actor=account_full_name(account),
        role=account["role"],
        detail=f"count={len(rows)}",
    )

    return len(rows)
