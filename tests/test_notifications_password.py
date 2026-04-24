import pytest

flask = pytest.importorskip("flask")

from lunch_platform.core.db import query
from .conftest import login


def test_bootstrap_admin_has_password_change_notification(client, app):
    response = login(client, 'admin', 'heslo123')
    assert response.status_code == 302
    page = client.get('/profile')
    text = page.get_data(as_text=True)
    assert 'Změna hesla' in text
    assert 'výchozí nebo resetované heslo' in text


def test_admin_can_change_password_and_clear_required_flag(client, app):
    login(client, 'admin', 'heslo123')
    with client.session_transaction() as sess:
        csrf = sess['csrf_token']
    response = client.post('/profile/password', data={
        'csrf_token': csrf,
        'current_password': 'heslo123',
        'new_password': 'newsecure123',
        'confirm_password': 'newsecure123',
    }, follow_redirects=False)
    assert response.status_code == 302
    with app.app_context():
        acct = query("SELECT * FROM accounts WHERE username='admin'", one=True)
        assert acct['must_change_password'] == 0
