import pytest

flask = pytest.importorskip("flask")

from lunch_platform.core.db import execute, query
from .conftest import login, register


def _set_role(app, email: str, role: str):
    with app.app_context():
        account = query("SELECT * FROM accounts WHERE email=?", (email,), one=True)
        execute("UPDATE accounts SET role=? WHERE id=?", (role, account["id"]))


def test_billing_admin_can_lock_and_pay_orders(client, app):
    register(client, "bill@example.com", "Billing", "Boss")
    register(client, "user1@example.com", "User", "One")
    _set_role(app, "bill@example.com", "billing_admin")

    login(client, "user1@example.com")
    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]
    client.post("/order-api", data={"day": "Pondělí", "dish_id": 1, "csrf_token": csrf})

    with app.app_context():
        user = query("SELECT * FROM accounts WHERE email='user1@example.com'", one=True)
        execute("UPDATE orders SET status='submitted' WHERE created_by_account_id=?", (user["id"],))

    login(client, "bill@example.com")
    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post("/admin/billing/lock-week", data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        user = query("SELECT * FROM accounts WHERE email='user1@example.com'", one=True)
        order = query("SELECT * FROM orders WHERE created_by_account_id=?", (user["id"],), one=True)
        assert order["status"] == "locked"

        execute("UPDATE orders SET status='invoiced' WHERE id=?", (order["id"],))

    response = client.post("/admin/billing/mark-paid", data={"target_account_id": user["id"], "csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        order = query("SELECT * FROM orders WHERE created_by_account_id=?", (user["id"],), one=True)
        assert order["status"] == "paid"
        assert order["paid_at"] is not None


def test_manager_cannot_use_billing_routes(client, app):
    register(client, "mgr@example.com", "Manager", "User")
    _set_role(app, "mgr@example.com", "manager")
    login(client, "mgr@example.com")
    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post("/admin/billing/pay-all", data={"csrf_token": csrf})
    assert response.status_code == 403
