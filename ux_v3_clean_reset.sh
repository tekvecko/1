#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=== UX V3 CLEAN RESET ==="

# BACKUP
cp lunch_platform/templates/orders/index.html lunch_platform/templates/orders/index.html.bak_v3 || true

python - <<'PY'
from pathlib import Path
import re

p = Path("lunch_platform/templates/orders/index.html")
t = p.read_text()

# 1) REMOVE mobile-day-rail celý blok
t = re.sub(r'<section class="mobile-day-rail".*?</section>', '', t, flags=re.S)

# 2) REMOVE mobile-smart-cart celý blok
t = re.sub(r'<section class="mobile-smart-cart.*?</section>', '', t, flags=re.S)

# 3) REMOVE hidden cart rail tab
t = t.replace('data-cart-rail-tab="true" style="display:none"', '')

# 4) REMOVE duplicity atributů
t = t.replace('data-menu-ux-v2-day-tabs="true" data-menu-ux-v2-day-tabs="true"', 'data-menu-ux-v2-day-tabs="true"')

# 5) CLEAN repeated attributes
t = t.replace('data-menu-ux-v2-card="true" data-menu-ux-v2-card="true" data-menu-ux-v2-card="true"', 'data-menu-ux-v2-card="true"')

p.write_text(t)
print("template cleaned for v3")
PY

echo "[✓] TEMPLATE CLEAN"
