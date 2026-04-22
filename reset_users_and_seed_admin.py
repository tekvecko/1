from pathlib import Path
import sqlite3
from werkzeug.security import generate_password_hash

DB = Path('instance/lunch_platform.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.executescript("""
DELETE FROM notifications;
DELETE FROM ratings;
DELETE FROM orders;
DELETE FROM users;
DELETE FROM accounts;
DELETE FROM audit_log;
""")
cur.execute(
    """
    INSERT INTO accounts(username, display_name, first_name, last_name, email, password_hash, must_change_password, role, is_active)
    VALUES (?, ?, ?, ?, ?, ?, 1, 'super_admin', 1)
    """,
    ('admin', 'System Admin', 'System', 'Admin', 'admin@local.invalid', generate_password_hash('heslo123')),
)
account_id = cur.lastrowid
cur.execute("INSERT INTO users(account_id, allergens) VALUES(?, '')", (account_id,))
cur.execute(
    "INSERT INTO notifications(account_id, title, body, link_url, level, kind, dedupe_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
    (account_id, 'Změňte výchozí heslo', 'Používáte výchozí heslo admin / heslo123. Změňte ho v profilu.', '/profile#password-change', 'warning', 'security', 'password_change_required'),
)
conn.commit()
conn.close()
print('Database reset complete.')
print('login: admin')
print('password: heslo123')
