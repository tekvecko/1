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
