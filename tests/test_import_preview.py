from lunch_platform.domain.menu_parser import analyze_menu_text


def test_analyze_menu_text_reports_missing_prices_and_suspicious_lines():
    text = """
    Restaurace U Někoho
    kontakt: 777 111 222
    Pondělí 21.4.2026
    1. Kuřecí steak
    Středa
    ???
    1. Smažený sýr 149 Kč
    """
    report = analyze_menu_text(text)

    assert report["recognized_days"] == ["Pondělí", "Středa"]
    assert "Úterý" in report["missing_days"]
    assert any(item["dish_name"] == "Kuřecí steak" for item in report["missing_price_items"])
    assert any(row["reason"] == "header_noise" for row in report["skipped_lines"])
    assert any(row["text"] == "???" for row in report["suspicious_lines"])



def test_analyze_menu_text_keeps_day_sections_and_multiline_context():
    text = """
    Úterý
    1. Kuřecí kapsa se sýrem
    a šunkou 159 Kč
    """
    report = analyze_menu_text(text)

    assert report["day_sections"][1]["day"] == "Úterý"
    parsed = report["day_sections"][1]["parsed_items"][0]
    assert parsed["dish_name"] == "Kuřecí kapsa se sýrem a šunkou"
    assert parsed["continued_lines"]
