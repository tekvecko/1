from .conftest import login

def test_debug_admin_login_session(client):
    r = login(client, "admin", "heslo123")
    print("LOGIN STATUS", r.status_code, r.headers.get("Location"))
    with client.session_transaction() as sess:
        print("SESSION", dict(sess))
    assert sess.get("account_id")
