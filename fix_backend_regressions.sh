#!/data/data/com.termux/files/usr/bin/bash
set -e

cp lunch_platform/services/billing.py lunch_platform/services/billing.py.bak_backend_fix || true
cp lunch_platform/services/imports.py lunch_platform/services/imports.py.bak_backend_fix || true

python - <<'PY'
from pathlib import Path

# 1) billing.py: chybí account_full_name import
p = Path("lunch_platform/services/billing.py")
t = p.read_text(encoding="utf-8")

if "account_full_name" not in t.splitlines()[2]:
    t = t.replace(
        "from ..core.db import execute, get_setting, log_event, query, set_setting",
        "from ..core.db import execute, get_setting, log_event, query, set_setting, account_full_name"
    )

p.write_text(t, encoding="utf-8")
print("billing import fixed")

# 2) imports.py: ručně přidaná položka bez ceny se musí počítat jako missing_price
p = Path("lunch_platform/services/imports.py")
t = p.read_text(encoding="utf-8")

old = """        raw_price = str(item.get("price_text") or "").strip()
        price_cents = extract_price_cents(raw_price)
        had_explicit_price = bool(raw_price and price_cents > 0)
        if price_cents <= 0:
            price_cents = DEFAULT_PRICE_CENTS
            raw_price = ""
            had_explicit_price = False
"""

new = """        raw_price_source = normalize_spaces(str(item.get("price_source") or ""))
        raw_price_text = normalize_spaces(str(item.get("price_text") or ""))
        stored_had_explicit = item.get("had_explicit_price")

        if stored_had_explicit is False:
            raw_price = raw_price_source
            had_explicit_price = False
            price_cents = extract_price_cents(raw_price)
            if price_cents <= 0:
                price_cents = DEFAULT_PRICE_CENTS
        else:
            raw_price = raw_price_source or raw_price_text
            price_cents = extract_price_cents(raw_price)
            had_explicit_price = bool(raw_price and price_cents > 0)
            if price_cents <= 0:
                price_cents = DEFAULT_PRICE_CENTS
                raw_price = ""
                had_explicit_price = False
"""

if old in t:
    t = t.replace(old, new)
else:
    print("imports price block already changed or not found")

t = t.replace(
    '''            "price_source": raw_price if had_explicit_price else "",''',
    '''            "price_source": raw_price_source if had_explicit_price else "",'''
)

t = t.replace(
"""            item["price_text"] = price_text
            item["manual"] = bool(item.get("manual")) or item.get("source_line") in (None, "")
            item["edited"] = True
""",
"""            item["price_text"] = price_text
            item["price_source"] = price_text.strip()
            item["had_explicit_price"] = bool(price_text.strip())
            item["manual"] = bool(item.get("manual")) or item.get("source_line") in (None, "")
            item["edited"] = True
"""
)

t = t.replace(
"""        "price_text": price_text,
        "source_line": "",
        "source_text": "Manuálně přidané v preview",
        "had_explicit_price": bool(price_text.strip()),
""",
"""        "price_text": price_text,
        "price_source": price_text.strip(),
        "source_line": "",
        "source_text": "Manuálně přidané v preview",
        "had_explicit_price": bool(price_text.strip()),
"""
)

p.write_text(t, encoding="utf-8")
print("imports missing price fixed")
PY

pytest -q
