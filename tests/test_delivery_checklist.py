from lunch_platform.core.db import execute, query
from .conftest import login, register


def test_manager_can_open_delivery_today(client, app):
    register(client, "delivery@example.com", "Delivery", "Admin")

    with app.app_context():
        execute("UPDATE accounts SET role='manager' WHERE email='delivery@example.com'")

    login(client, "delivery@example.com")

    response = client.get("/admin/delivery/today")
    assert response.status_code == 200
    assert "Výdej dnes" in response.get_data(as_text=True)


def test_manager_can_mark_delivery_received(client, app):
    register(client, "delivery2@example.com", "Delivery", "Boss")
    register(client, "worker@example.com", "Worker", "One")

    with app.app_context():
        execute("UPDATE accounts SET role='manager' WHERE email='delivery2@example.com'")
        worker = query("SELECT * FROM accounts WHERE email='worker@example.com'", one=True)
        execute(
            """
            INSERT INTO orders(created_by_account_id, day, dish_id, price_snapshot_cents, status)
            VALUES (?, 'Pondělí', 1, 15000, 'submitted')
            """,
            (worker["id"],),
        )

    login(client, "delivery2@example.com")

    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post("/admin/delivery/today/received", data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 302
