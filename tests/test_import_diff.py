import pytest

flask = pytest.importorskip("flask")

from lunch_platform.services.imports import build_menu_diff


class FakeRow(dict):
    pass


def test_build_menu_diff_detects_added_removed_and_price_changes():
    current_rows = [
        FakeRow(id=1, day='Pondělí', dish_name='Kuřecí steak', price_text='150 Kč', price_cents=15000),
        FakeRow(id=2, day='Úterý', dish_name='Hovězí guláš', price_text='165 Kč', price_cents=16500),
    ]
    parsed_items = [
        {'day': 'Pondělí', 'dish_name': 'Kuřecí steak', 'price_text': '155 Kč', 'price_cents': 15500, 'source_line': 4},
        {'day': 'Středa', 'dish_name': 'Smažený sýr', 'price_text': '149 Kč', 'price_cents': 14900, 'source_line': 8},
    ]

    diff = build_menu_diff(parsed_items, current_rows)

    assert diff['summary']['added_count'] == 1
    assert diff['summary']['removed_count'] == 1
    assert diff['summary']['changed_count'] == 1
    assert diff['added'][0]['dish_name'] == 'Smažený sýr'
    assert diff['changed'][0]['old_price_text'] == '150 Kč'
    assert diff['removed'][0]['dish_name'] == 'Hovězí guláš'
