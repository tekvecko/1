def test_place_order_rejects_dish_from_other_day(app):
    from lunch_platform.core.db import execute, query
    from lunch_platform.services.orders import place_order

    with app.app_context():
        acct = query("SELECT * FROM accounts WHERE username='admin'", one=True)
        execute("INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES (?, ?, ?, ?)", ("Pondělí", "A", "100 Kč", 10000))
        execute("INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES (?, ?, ?, ?)", ("Úterý", "B", "120 Kč", 12000))
        tue = query("SELECT * FROM menu WHERE day='Úterý' ORDER BY id DESC", one=True)
        try:
            place_order(acct, "Pondělí", tue["id"])
        except ValueError as exc:
            assert "one lunch" in str(exc)
        else:
            raise AssertionError("Expected ValueError")


def test_day_status_map_shows_paid_and_selected(app):
    from lunch_platform.core.db import execute, query
    from lunch_platform.services.orders import build_menu_view_model

    with app.app_context():
        acct = query("SELECT * FROM accounts WHERE username='admin'", one=True)
        execute("INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES (?, ?, ?, ?)", ("Pondělí", "A", "100 Kč", 10000))
        execute("INSERT INTO menu(day, dish_name, price_text, price_cents) VALUES (?, ?, ?, ?)", ("Úterý", "B", "120 Kč", 12000))
        mon = query("SELECT * FROM menu WHERE day='Pondělí' ORDER BY id DESC", one=True)
        tue = query("SELECT * FROM menu WHERE day='Úterý' ORDER BY id DESC", one=True)
        execute("INSERT INTO orders(created_by_account_id, day, dish_id, status, dish_name_snapshot, price_snapshot_text, price_snapshot_cents) VALUES (?, ?, ?, 'paid', ?, ?, ?)", (acct['id'], 'Pondělí', mon['id'], mon['dish_name'], mon['price_text'], mon['price_cents']))
        execute("INSERT INTO orders(created_by_account_id, day, dish_id, status, dish_name_snapshot, price_snapshot_text, price_snapshot_cents) VALUES (?, ?, ?, 'draft', ?, ?, ?)", (acct['id'], 'Úterý', tue['id'], tue['dish_name'], tue['price_text'], tue['price_cents']))
        state = build_menu_view_model(acct['id'])
        assert state['day_status_by_day']['Pondělí'] == 'paid'
        assert state['day_status_by_day']['Úterý'] == 'selected'
