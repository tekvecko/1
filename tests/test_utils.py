from lunch_platform.core.utils import dish_key, extract_price_cents, normalize_user_name


def test_normalize_user_name_strips_unsafe_chars():
    assert normalize_user_name("  Jiří <script>  ") == "Jiří script"


def test_extract_price_cents_handles_czk_text():
    assert extract_price_cents("150 Kč") == 15000
    assert extract_price_cents("89,50 Kč") == 8950


def test_dish_key_is_stable_without_diacritics():
    assert dish_key("Řízek s kaší") == "rizek s kasi"
