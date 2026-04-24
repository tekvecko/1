import pytest

flask = pytest.importorskip("flask")

from lunch_platform.core.db import query
from .conftest import login, register


def test_registration_login_and_order_flow(client, app):
    response = register(client, "alice@example.com", "Alice", "Worker")
    assert response.status_code == 200

    response = login(client, "alice@example.com")
    assert response.status_code == 302

    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post("/order-api", data={"day": "Pondělí", "dish_id": 1, "csrf_token": csrf})
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    with app.app_context():
        alice = query("SELECT * FROM accounts WHERE email='alice@example.com'", one=True)
        order = query("SELECT * FROM orders WHERE created_by_account_id=?", (alice["id"],), one=True)
        assert order["price_snapshot_cents"] == 15000
        assert order["dish_name_snapshot"] == "Kuřecí řízek"


def test_csrf_protects_write_routes(client):
    response = client.post("/register", data={
        "first_name": "Bob",
        "last_name": "User",
        "email": "bob@example.com",
        "password": "supersecret",
        "password_confirm": "supersecret",
    })
    assert response.status_code == 403


def test_regular_user_cannot_access_admin_dashboard(client):
    register(client, "basic@example.com", "Basic", "User")
    login(client, "basic@example.com")
    response = client.get("/admin")
    assert response.status_code == 403


def test_profile_write_uses_logged_in_account_only(client, app):
    register(client, "alice2@example.com", "Alice", "Two")
    register(client, "eve@example.com", "Eve", "User")
    login(client, "alice2@example.com")
    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post("/profile?user=Eve", data={"allergens": "milk", "csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        alice = query("SELECT * FROM accounts WHERE email='alice2@example.com'", one=True)
        eve = query("SELECT * FROM accounts WHERE email='eve@example.com'", one=True)
        alice_profile = query("SELECT * FROM users WHERE account_id=?", (alice["id"],), one=True)
        eve_profile = query("SELECT * FROM users WHERE account_id=?", (eve["id"],), one=True)
        assert alice_profile["allergens"] == "milk"
        assert eve_profile["allergens"] == ""
