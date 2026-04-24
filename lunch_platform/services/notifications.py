from __future__ import annotations

from ..core.db import execute, query

PASSWORD_CHANGE_KEY = "password_change_required"


def create_notification(account_id: int, title: str, body: str = "", *, link_url: str = "", level: str = "info", kind: str = "generic", dedupe_key: str | None = None) -> None:
    if dedupe_key:
        existing = query(
            "SELECT id FROM notifications WHERE account_id=? AND dedupe_key=? AND read_at IS NULL",
            (account_id, dedupe_key),
            one=True,
        )
        if existing:
            return
    execute(
        """
        INSERT INTO notifications(account_id, title, body, link_url, level, kind, dedupe_key)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (account_id, title, body, link_url, level, kind, dedupe_key or ""),
    )



def list_notifications(account_id: int, *, unread_only: bool = False):
    if unread_only:
        return query(
            "SELECT * FROM notifications WHERE account_id=? AND read_at IS NULL ORDER BY id DESC LIMIT 20",
            (account_id,),
        )
    return query("SELECT * FROM notifications WHERE account_id=? ORDER BY id DESC LIMIT 20", (account_id,))



def unread_notification_count(account_id: int) -> int:
    row = query(
        "SELECT COUNT(*) AS c FROM notifications WHERE account_id=? AND read_at IS NULL",
        (account_id,),
        one=True,
    )
    return int(row["c"] if row else 0)



def mark_notification_read(account_id: int, notification_id: int) -> None:
    execute(
        "UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE id=? AND account_id=?",
        (notification_id, account_id),
    )



def sync_password_change_notification(account) -> None:
    if account["must_change_password"]:
        create_notification(
            account["id"],
            "Změňte výchozí heslo",
            "Účet stále používá výchozí nebo resetované heslo. Bezpečnostně je potřeba ho změnit.",
            link_url="/profile#password-change",
            level="warning",
            kind="security",
            dedupe_key=PASSWORD_CHANGE_KEY,
        )
    else:
        execute(
            "UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE account_id=? AND dedupe_key=? AND read_at IS NULL",
            (account["id"], PASSWORD_CHANGE_KEY),
        )
