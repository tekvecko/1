import pytest

flask = pytest.importorskip("flask")

from lunch_platform.core.db import query, execute
from .conftest import get_csrf, login, register


def test_super_admin_can_create_and_update_account(client, app):
    with app.app_context():
        execute("UPDATE accounts SET must_change_password=0 WHERE username='admin'")

    login(client, "admin", "heslo123")
    with client.session_transaction() as sess:
        assert sess.get("account_id") is not None
        csrf = sess["csrf_token"]

    response = client.post("/admin/accounts/create", data={
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "email": "newuser@example.com",
        "role": "manager",
        "password": "supersecret",
        "password_confirm": "supersecret",
        "csrf_token": csrf,
    }, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        row = query("SELECT * FROM accounts WHERE username='newuser'", one=True)
        assert row is not None
        assert row["email"] == "newuser@example.com"
        assert row["first_name"] == "New"
        assert row["role"] == "manager"
        account_id = row["id"]

    response = client.post(f"/admin/accounts/{account_id}/profile", data={
        "first_name": "Better",
        "last_name": "Name",
        "email": "better@example.com",
        "csrf_token": csrf,
    }, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        row = query("SELECT * FROM accounts WHERE username='newuser'", one=True)
        assert row["first_name"] == "Better"
        assert row["email"] == "better@example.com"


def test_super_admin_can_delete_regular_account(client, app):
    with app.app_context():
        execute("UPDATE accounts SET must_change_password=0 WHERE username='admin'")

    login(client, "admin", "heslo123")
    with client.session_transaction() as sess:
        assert sess.get("account_id") is not None
        csrf = sess["csrf_token"]

    client.post("/admin/accounts/create", data={
        "username": "todelete",
        "first_name": "Delete",
        "last_name": "Me",
        "email": "todelete@example.com",
        "role": "user",
        "password": "supersecret",
        "password_confirm": "supersecret",
        "csrf_token": csrf,
    }, follow_redirects=False)

    with app.app_context():
        row = query("SELECT * FROM accounts WHERE username='todelete'", one=True)
        assert row is not None
        account_id = row["id"]

    response = client.post(f"/admin/accounts/{account_id}/delete", data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        row = query("SELECT * FROM accounts WHERE username='todelete'", one=True)
        assert row is None


def test_register_requires_email_and_no_name_greeting_in_menu(client):
    csrf = get_csrf(client, '/register')
    response = client.post('/register', data={
        'username': 'mailmissing',
        'first_name': 'Mail',
        'last_name': 'Missing',
        'email': '',
        'password': 'supersecret',
        'password_confirm': 'supersecret',
        'csrf_token': csrf,
    }, follow_redirects=True)
    assert b'Vypl' in response.data

    register(client, "neutralui@example.com", "Neutral", "User")
    login(client, "neutralui@example.com")
    response = client.get("/")
    assert b'Ahoj' not in response.data
