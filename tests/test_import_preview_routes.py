import io

import pytest

flask = pytest.importorskip("flask")

from lunch_platform.core.db import query
from .conftest import login, register
from .test_billing_and_roles import _set_role



def test_manager_can_open_preview_and_apply_import(client, app, monkeypatch):
    register(client, "mgr2@example.com", "Manager", "Two")
    _set_role(app, "mgr2@example.com", "manager")
    login(client, "mgr2@example.com")

    preview_report = {
        "items": [
            {
                "day": "Pondělí",
                "dish_name": "Nový steak",
                "price_cents": 17000,
                "price_text": "170 Kč",
                "source_line": 4,
                "had_explicit_price": True,
                "continued_lines": [],
            }
        ],
        "recognized_days": ["Pondělí"],
        "missing_days": ["Úterý", "Středa", "Čtvrtek", "Pátek"],
        "missing_price_items": [],
        "skipped_lines": [],
        "suspicious_lines": [],
        "preamble_lines": [],
        "day_sections": [],
        "summary": {
            "recognized_day_count": 1,
            "parsed_item_count": 1,
            "missing_price_count": 0,
            "skipped_line_count": 0,
            "suspicious_line_count": 0,
        },
        "diff": {"added": [], "removed": [], "changed": [], "summary": {"added_count": 0, "removed_count": 0, "changed_count": 0, "unchanged_count": 0}},
        "meta": {"original_filename": "menu.pdf", "parsed_with": "pdfminer"},
    }

    monkeypatch.setattr("lunch_platform.imports.routes.parse_menu_pdf_preview", lambda *_args, **_kwargs: preview_report)

    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post(
        "/admin/imports/preview",
        data={"csrf_token": csrf, "pdf_file": (io.BytesIO(b"%PDF fake"), "menu.pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    preview_url = response.headers["Location"]
    assert "/admin/imports/preview/" in preview_url

    response = client.get(preview_url)
    assert response.status_code == 200
    assert b"PDF preview before save" in response.data

    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]
    response = client.post(preview_url.replace("/preview/", "/apply/"), data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 302

    with app.app_context():
        menu = query("SELECT day, dish_name, price_cents FROM menu ORDER BY id")
        assert len(menu) == 1
        assert menu[0]["dish_name"] == "Nový steak"
        assert menu[0]["price_cents"] == 17000

    response = client.get('/admin/imports/pdf/current')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'



def test_manager_can_edit_add_and_delete_preview_items(client, app):
    register(client, "mgr3@example.com", "Manager", "Three")
    _set_role(app, "mgr3@example.com", "manager")
    login(client, "mgr3@example.com")

    from lunch_platform.services.imports import save_preview_report

    preview_report = {
        "items": [
            {
                "item_id": "item-one",
                "day": "Pondělí",
                "dish_name": "Špatně rozpoznané jídlo",
                "price_cents": 15000,
                "price_text": "150 Kč",
                "source_line": 7,
                "source_text": "1. Špatně rozpoznané jídlo 150 Kč",
                "had_explicit_price": True,
                "continued_lines": [],
            }
        ],
        "recognized_days": ["Pondělí"],
        "missing_days": ["Úterý", "Středa", "Čtvrtek", "Pátek"],
        "missing_price_items": [],
        "skipped_lines": [],
        "suspicious_lines": [],
        "preamble_lines": [],
        "day_sections": [],
        "summary": {
            "recognized_day_count": 1,
            "parsed_item_count": 1,
            "missing_price_count": 0,
            "skipped_line_count": 0,
            "suspicious_line_count": 0,
        },
        "diff": {"added": [], "removed": [], "changed": [], "summary": {"added_count": 0, "removed_count": 0, "changed_count": 0, "unchanged_count": 0}},
        "meta": {"original_filename": "menu.pdf", "parsed_with": "pdfminer"},
    }
    with app.app_context():
        preview_id = save_preview_report(preview_report, preview_id="editme")

    with client.session_transaction() as sess:
        csrf = sess["csrf_token"]

    response = client.post(
        f"/admin/imports/preview/{preview_id}/item/item-one/update",
        data={"csrf_token": csrf, "day": "Úterý", "dish_name": "Opravené jídlo", "price_text": "179 Kč"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    response = client.post(
        f"/admin/imports/preview/{preview_id}/item/add",
        data={"csrf_token": csrf, "day": "Středa", "dish_name": "Ruční doplnění", "price_text": ""},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        from lunch_platform.services.imports import load_preview_report
        report = load_preview_report(preview_id)
        assert any(item["dish_name"] == "Opravené jídlo" and item["day"] == "Úterý" for item in report["items"])
        assert any(item["dish_name"] == "Ruční doplnění" and item["manual"] for item in report["items"])
        assert report["summary"]["missing_price_count"] == 1
        added_item = next(item for item in report["items"] if item["dish_name"] == "Ruční doplnění")

    response = client.post(
        f"/admin/imports/preview/{preview_id}/item/{added_item['item_id']}/delete",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        from lunch_platform.services.imports import load_preview_report
        report = load_preview_report(preview_id)
        assert all(item["dish_name"] != "Ruční doplnění" for item in report["items"])
        assert any(item["dish_name"] == "Opravené jídlo" for item in report["items"])
