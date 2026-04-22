from lunch_platform.domain.menu_parser import parse_menu_text


def test_parse_menu_text_extracts_days_dishes_and_prices():
    text = """
    Pondělí
    0,3 l Rajská polévka
    1. Kuřecí steak 150 Kč
    2. Těstoviny Alfredo 139 Kč
    Úterý
    1. Hovězí guláš 165 Kč
    """
    items = parse_menu_text(text)
    assert items[0][0] == 'Pondělí'
    assert items[0][1].startswith('Polévka:')
    assert items[1] == ('Pondělí', 'Kuřecí steak', 15000)
    assert items[2] == ('Pondělí', 'Těstoviny Alfredo', 13900)
    assert items[3] == ('Úterý', 'Hovězí guláš', 16500)


def test_parse_menu_text_handles_dates_and_multiline_dishes():
    text = """
    Pondělí 21.4.2026
    1. Kuřecí kapsa se sýrem
    a šunkou, bramborová kaše 159 Kč
    2. Salát: Caesar s kuřetem 149 Kč
    Út 22.4.
    Polévka: Kulajda 45 Kč
    1) Hovězí pečeně 169 Kč
    """
    items = parse_menu_text(text)
    assert ('Pondělí', 'Kuřecí kapsa se sýrem a šunkou, bramborová kaše', 15900) in items
    assert ('Pondělí', 'Caesar s kuřetem', 14900) in items
    assert ('Úterý', 'Polévka: Kulajda', 4500) in items
    assert ('Úterý', 'Hovězí pečeně', 16900) in items


def test_parse_menu_text_ignores_header_noise_and_keeps_default_price():
    text = """
    Restaurace U Někoho
    www.restaurace.cz
    Tel: 777 111 222
    Středa
    1. Smažený sýr, hranolky
    """
    items = parse_menu_text(text)
    assert items == [('Středa', 'Smažený sýr, hranolky', 15000)]
