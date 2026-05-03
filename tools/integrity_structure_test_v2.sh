#!/data/data/com.termux/files/usr/bin/bash
set -u

PROJECT_DIR="$(pwd)"
TS="$(date +%Y%m%d_%H%M%S)"
REPORT="integrity_report_v2_$TS.txt"
TMP_DIR="$PROJECT_DIR/.integrity_tmp"

mkdir -p "$TMP_DIR"

PASS=0
FAIL=0
WARN=0

line() {
  echo "============================================================" | tee -a "$REPORT"
}

section() {
  echo | tee -a "$REPORT"
  line
  echo "$1" | tee -a "$REPORT"
  line
}

ok() {
  PASS=$((PASS+1))
  echo "[OK] $1" | tee -a "$REPORT"
}

fail() {
  FAIL=$((FAIL+1))
  echo "[FAIL] $1" | tee -a "$REPORT"
}

warn() {
  WARN=$((WARN+1))
  echo "[WARN] $1" | tee -a "$REPORT"
}

check_file() {
  local f="$1"
  if [ -f "$f" ]; then
    ok "Soubor existuje: $f"
  else
    fail "Chybí soubor: $f"
  fi
}

check_dir() {
  local d="$1"
  if [ -d "$d" ]; then
    ok "Adresář existuje: $d"
  else
    fail "Chybí adresář: $d"
  fi
}

contains_any() {
  local file="$1"
  shift

  for pattern in "$@"; do
    if grep -q "$pattern" "$file" 2>/dev/null; then
      return 0
    fi
  done

  return 1
}

count_any() {
  local file="$1"
  shift

  local total=0
  local c=0

  for pattern in "$@"; do
    c="$(grep -o "$pattern" "$file" 2>/dev/null | wc -l | tr -d ' ')"
    total=$((total + c))
  done

  echo "$total"
}

echo "FINAL LUNCH - INTEGRITY / STRUCTURE TEST V2" | tee "$REPORT"
echo "Project: $PROJECT_DIR" | tee -a "$REPORT"
echo "Time: $TS" | tee -a "$REPORT"
echo "Temp: $TMP_DIR" | tee -a "$REPORT"

section "1) KRITICKÁ STRUKTURA PROJEKTU"

check_file "app.py"
check_file "requirements.txt"
check_file "pytest.ini"
check_file "README.md"

check_dir "lunch_platform"
check_file "lunch_platform/__init__.py"

check_dir "lunch_platform/core"
check_file "lunch_platform/core/db.py"
check_file "lunch_platform/core/auth.py"
check_file "lunch_platform/core/config.py"
check_file "lunch_platform/core/security.py"
check_file "lunch_platform/core/utils.py"

check_dir "lunch_platform/orders"
check_file "lunch_platform/orders/routes.py"
check_file "lunch_platform/services/orders.py"

check_dir "lunch_platform/admin"
check_file "lunch_platform/admin/routes.py"

check_dir "lunch_platform/templates"
check_file "lunch_platform/templates/base.html"
check_file "lunch_platform/templates/orders/index.html"
check_file "lunch_platform/templates/orders/report.html"
check_file "lunch_platform/templates/orders/profile.html"
check_file "lunch_platform/templates/admin/dashboard.html"

check_dir "lunch_platform/static"
check_file "lunch_platform/static/app.js"
check_file "lunch_platform/static/navy.css"
check_file "lunch_platform/static/v4.css"

check_dir "tests"

section "2) PYTHON / FLASK IMPORT TEST"

python - <<'PY' >> "$REPORT" 2>&1
from lunch_platform import create_app

app = create_app({"TESTING": True})
print("[PY-OK] APP IMPORT OK")
print("[PY-OK] ROUTE COUNT:", len(list(app.url_map.iter_rules())))

for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    print(f"[ROUTE] {r.rule} -> {r.endpoint} {sorted(r.methods)}")
PY

if [ "$?" -eq 0 ]; then
  ok "Flask aplikace jde importovat"
else
  fail "Flask aplikace nejde importovat"
fi

section "3) ROUTE INTEGRITY"

ROUTE_OUT="$TMP_DIR/lunch_routes_check_$TS.txt"

python - <<'PY' > "$ROUTE_OUT" 2>&1
from lunch_platform import create_app

app = create_app({"TESTING": True})
routes = {r.rule: r.endpoint for r in app.url_map.iter_rules()}

required = {
    "/": "orders.index",
    "/orders": "orders.orders_report",
    "/profile": "orders.profile",
    "/admin": "admin.dashboard",
    "/order-api": "orders.order_api",
    "/order-api/cancel": "orders.order_api_cancel",
    "/login": "auth.login",
    "/logout": "auth.logout",
}

failed = False

for rule, endpoint in required.items():
    got = routes.get(rule)
    if got == endpoint:
        print(f"[OK] {rule} -> {endpoint}")
    else:
        print(f"[FAIL] {rule}: expected {endpoint}, got {got}")
        failed = True

raise SystemExit(1 if failed else 0)
PY

ROUTE_CODE="$?"
cat "$ROUTE_OUT" | tee -a "$REPORT"

if [ "$ROUTE_CODE" -eq 0 ]; then
  ok "Kritické routy jsou správně dostupné"
else
  fail "Některé kritické routy chybí nebo míří jinam"
fi

section "4) BASE TEMPLATE / NAVIGACE"

BASE="lunch_platform/templates/base.html"

if [ -f "$BASE" ]; then
  APP_BOTTOM_COUNT="$(grep -o 'app-bottom-nav' "$BASE" | wc -l | tr -d ' ')"
  QUICK_COUNT="$(grep -o 'Rychlé akce' "$BASE" | wc -l | tr -d ' ')"
  NATIVE_SHEET_COUNT="$(grep -o 'native-more-sheet' "$BASE" | wc -l | tr -d ' ')"
  SMART_BOTTOM_COUNT="$(grep -o 'smart-bottom' "$BASE" | wc -l | tr -d ' ')"
  BRAND_FINAL_COUNT="$(grep -o 'FINAL LUNCH' "$BASE" | wc -l | tr -d ' ')"
  BRAND_CLASS_COUNT="$(grep -o 'brand-copy\|brand-mark\|glass-nav' "$BASE" | wc -l | tr -d ' ')"

  echo "app-bottom-nav count: $APP_BOTTOM_COUNT" | tee -a "$REPORT"
  echo "Rychlé akce count: $QUICK_COUNT" | tee -a "$REPORT"
  echo "native-more-sheet count: $NATIVE_SHEET_COUNT" | tee -a "$REPORT"
  echo "smart-bottom count: $SMART_BOTTOM_COUNT" | tee -a "$REPORT"
  echo "FINAL LUNCH literal count: $BRAND_FINAL_COUNT" | tee -a "$REPORT"
  echo "brand/glass-nav marker count: $BRAND_CLASS_COUNT" | tee -a "$REPORT"

  if [ "$APP_BOTTOM_COUNT" -eq 1 ]; then
    ok "Spodní navigace je v base.html právě jednou"
  else
    fail "Spodní navigace app-bottom-nav má být přesně 1×, aktuálně: $APP_BOTTOM_COUNT"
  fi

  if [ "$QUICK_COUNT" -eq 0 ]; then
    ok "V base.html nezůstaly syrové texty 'Rychlé akce'"
  else
    fail "V base.html stále zůstává syrový text 'Rychlé akce'"
  fi

  if [ "$NATIVE_SHEET_COUNT" -eq 0 ]; then
    ok "V base.html nezůstává native-more-sheet"
  else
    warn "V base.html je native-more-sheet: $NATIVE_SHEET_COUNT×"
  fi

  if [ "$SMART_BOTTOM_COUNT" -eq 0 ]; then
    ok "V base.html nezůstává smart-bottom"
  else
    warn "V base.html je smart-bottom: $SMART_BOTTOM_COUNT×"
  fi

  if [ "$BRAND_CLASS_COUNT" -ge 1 ]; then
    ok "Base template obsahuje brand/nav strukturu"
  else
    warn "Base template nemá jasný brand/glass-nav marker"
  fi
else
  fail "base.html neexistuje"
fi

section "5) MENU TEMPLATE / KARTY JÍDEL / ORDER BUTTONS"

MENU="lunch_platform/templates/orders/index.html"

if [ -f "$MENU" ]; then
  if grep -q "data-select-day" "$MENU"; then
    ok "MENU obsahuje data-select-day"
  else
    fail "MENU neobsahuje data-select-day"
  fi

  if grep -q "data-select-dish-id" "$MENU"; then
    ok "MENU obsahuje data-select-dish-id"
  else
    fail "MENU neobsahuje data-select-dish-id"
  fi

  if grep -q "data-cancel-day" "$MENU"; then
    ok "MENU obsahuje data-cancel-day"
  else
    fail "MENU neobsahuje data-cancel-day"
  fi

  if contains_any "$MENU" \
    "uxv4-dish-card" \
    "dish-card" \
    "food-card" \
    "meal-card" \
    "menu-item-card" \
    "v7-order-card" \
    "article class=.*dish" \
    "article class=.*food"
  then
    ok "MENU obsahuje rozpoznatelné karty jídel"
  else
    fail "MENU neobsahuje rozpoznatelné karty jídel"
  fi

  if contains_any "$MENU" \
    "data-uxv4-dish-toggle" \
    "data-dish-toggle" \
    "data-open-dish" \
    "data-open-dish-modal" \
    "data-detail" \
    "dish-detail" \
    "meal-detail"
  then
    ok "MENU obsahuje mechanismus detailu jídla"
  else
    warn "MENU nemá jasný marker detailu jídla; může být řešeno přes klik na kartu v JS"
  fi

  SELECT_COUNT="$(grep -o 'data-select-day' "$MENU" | wc -l | tr -d ' ')"
  CANCEL_COUNT="$(grep -o 'data-cancel-day' "$MENU" | wc -l | tr -d ' ')"
  CARD_COUNT="$(count_any "$MENU" "uxv4-dish-card" "dish-card" "food-card" "meal-card" "menu-item-card")"

  echo "data-select-day count: $SELECT_COUNT" | tee -a "$REPORT"
  echo "data-cancel-day count: $CANCEL_COUNT" | tee -a "$REPORT"
  echo "dish-card compatible count: $CARD_COUNT" | tee -a "$REPORT"
else
  fail "MENU template neexistuje"
fi

section "6) REPORT TEMPLATE / OBJEDNÁVKY"

REPORT_TEMPLATE="lunch_platform/templates/orders/report.html"

if [ -f "$REPORT_TEMPLATE" ]; then
  for needle in \
    "v7-report-page" \
    "v7-report-hero" \
    "v7-order-card" \
    "v7-report-stats" \
    "Můj report"
  do
    if grep -q "$needle" "$REPORT_TEMPLATE"; then
      ok "REPORT template obsahuje: $needle"
    else
      fail "REPORT template neobsahuje: $needle"
    fi
  done
else
  fail "report.html neexistuje"
fi

section "7) ADMIN TEMPLATE / ADMIN TABY"

ADMIN="lunch_platform/templates/admin/dashboard.html"

if [ -f "$ADMIN" ]; then
  for needle in \
    "Menu" \
    "Billing" \
    "Účty" \
    "Audit"
  do
    if grep -qi "$needle" "$ADMIN"; then
      ok "ADMIN obsahuje text/tlačítko: $needle"
    else
      warn "ADMIN možná neobsahuje text/tlačítko: $needle"
    fi
  done

  if grep -q "data-admin-tabs\|admin-tabs\|admin-tabbar\|admin-section-tabs" "$ADMIN"; then
    ok "ADMIN má rozpoznatelný tab container"
  else
    warn "ADMIN nemá jasný tab container; JS fallback může fungovat přes text tlačítek, ale lepší je doplnit data-admin-tabs"
  fi
else
  fail "admin/dashboard.html neexistuje"
fi

section "8) JS INTEGRITA / ORDER API HANDLERY"

JS="lunch_platform/static/app.js"

if [ -f "$JS" ]; then
  if grep -q "/order-api" "$JS"; then
    ok "app.js obsahuje /order-api"
  else
    fail "app.js neobsahuje /order-api"
  fi

  if grep -q "data-select-day" "$JS"; then
    ok "app.js obsahuje data-select-day handler/marker"
  else
    fail "app.js neobsahuje data-select-day"
  fi

  if grep -q "data-cancel-day" "$JS"; then
    ok "app.js obsahuje data-cancel-day handler/marker"
  else
    fail "app.js neobsahuje data-cancel-day"
  fi

  if grep -q "V7 ADMIN MOBILE TABS FALLBACK" "$JS"; then
    ok "app.js obsahuje V7 admin tabs fallback"
  else
    warn "app.js neobsahuje V7 admin tabs fallback"
  fi

  ORDER_API_COUNT="$(grep -o '/order-api' "$JS" | wc -l | tr -d ' ')"
  echo "/order-api references in app.js: $ORDER_API_COUNT" | tee -a "$REPORT"

  if [ "$ORDER_API_COUNT" -ge 1 ]; then
    ok "app.js má odkazy na /order-api"
  else
    fail "app.js nemá žádný odkaz na /order-api"
  fi
else
  fail "app.js neexistuje"
fi

section "9) CSS INTEGRITA / DUPLICITY PATCHŮ"

for CSS in lunch_platform/static/v4.css lunch_platform/static/navy.css; do
  if [ -f "$CSS" ]; then
    echo "--- $CSS ---" | tee -a "$REPORT"

    for marker in \
      "REAL MOBILE SCREEN FIX V7" \
      "MENU BLUE NATIVE PANELS V2" \
      "V6 HARD CLEAN BOTTOM NAV"
    do
      C="$(grep -o "$marker" "$CSS" 2>/dev/null | wc -l | tr -d ' ')"
      echo "$marker count: $C" | tee -a "$REPORT"
      if [ "$C" -gt 3 ]; then
        warn "$CSS má hodně opakování markeru '$marker' ($C×)"
      fi
    done

    if grep -q 'body\[data-active-page="menu"\]' "$CSS"; then
      ok "$CSS obsahuje cílené styly pro MENU"
    else
      warn "$CSS neobsahuje body[data-active-page=\"menu\"]"
    fi

    if grep -q 'body\[data-active-page="orders"\]' "$CSS"; then
      ok "$CSS obsahuje cílené styly pro ORDERS"
    else
      warn "$CSS neobsahuje body[data-active-page=\"orders\"]"
    fi

    if grep -q 'body\[data-active-page="admin"\]' "$CSS"; then
      ok "$CSS obsahuje cílené styly pro ADMIN"
    else
      warn "$CSS neobsahuje body[data-active-page=\"admin\"]"
    fi
  else
    fail "$CSS neexistuje"
  fi
done

section "10) DATABÁZE / SCHÉMA"

DB_OUT="$TMP_DIR/lunch_db_check_$TS.txt"

python - <<'PY' > "$DB_OUT" 2>&1
from lunch_platform import create_app
from lunch_platform.core.db import get_db

app = create_app({"TESTING": True})

with app.app_context():
    con = get_db()
    cur = con.cursor()

    required_tables = ["menu", "orders", "accounts", "users"]
    failed = False

    for table in required_tables:
        row = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()

        if row:
            print(f"[OK] table exists: {table}")
        else:
            print(f"[FAIL] missing table: {table}")
            failed = True

    print("\n--- orders columns ---")
    cols = [dict(r) for r in cur.execute("PRAGMA table_info(orders)").fetchall()]
    for c in cols:
        print(c)

    col_names = {c["name"] for c in cols}

    required_columns = [
        "id",
        "created_by_account_id",
        "day",
        "dish_id",
        "status",
        "dish_name_snapshot",
        "price_snapshot_cents",
    ]

    for col in required_columns:
        if col in col_names:
            print(f"[OK] orders column: {col}")
        else:
            print(f"[FAIL] orders missing column: {col}")
            failed = True

    print("\n--- menu columns ---")
    menu_cols = [dict(r) for r in cur.execute("PRAGMA table_info(menu)").fetchall()]
    for c in menu_cols:
        print(c)

    menu_col_names = {c["name"] for c in menu_cols}
    if "restaurant_id" in menu_col_names:
        print("[OK] menu.restaurant_id exists")
    else:
        print("[WARN] menu.restaurant_id missing - multi-restaurant may be partial")

    print("\n--- orders indexes ---")
    indexes = [dict(r) for r in cur.execute("PRAGMA index_list(orders)").fetchall()]
    for idx in indexes:
        print(idx)
        idx_name = idx["name"]
        cols_idx = [
            dict(x) for x in cur.execute(f"PRAGMA index_info({idx_name})").fetchall()
        ]
        idx_cols = [x["name"] for x in cols_idx]
        print("  cols:", idx_cols)

        if idx["unique"] and idx_cols == ["created_by_account_id", "day"]:
            print("[FAIL] old single-restaurant UNIQUE(created_by_account_id, day) still exists")
            failed = True

    raise SystemExit(1 if failed else 0)
PY

DB_CODE="$?"
cat "$DB_OUT" | tee -a "$REPORT"

if [ "$DB_CODE" -eq 0 ]; then
  ok "Databázové schéma vypadá konzistentně"
else
  fail "Databázové schéma má problém"
fi

section "11) SERVICE API / FUNKCE OBJEDNÁVEK"

SERVICE_OUT="$TMP_DIR/lunch_service_check_$TS.txt"

python - <<'PY' > "$SERVICE_OUT" 2>&1
from lunch_platform import create_app

app = create_app({"TESTING": True})

with app.app_context():
    import lunch_platform.services.orders as o

    required = [
        "build_menu_view_model",
        "current_state",
        "place_order",
        "cancel_order",
        "get_menu",
        "get_user_orders",
    ]

    failed = False

    for name in required:
        if hasattr(o, name):
            print(f"[OK] service function exists: {name}")
        else:
            print(f"[FAIL] missing service function: {name}")
            failed = True

    raise SystemExit(1 if failed else 0)
PY

SERVICE_CODE="$?"
cat "$SERVICE_OUT" | tee -a "$REPORT"

if [ "$SERVICE_CODE" -eq 0 ]; then
  ok "Service funkce objednávek existují"
else
  fail "Chybí některé service funkce objednávek"
fi

section "12) TESTY PYTEST"

if command -v pytest >/dev/null 2>&1; then
  pytest -q | tee -a "$REPORT"
  PYTEST_CODE="${PIPESTATUS[0]}"

  if [ "$PYTEST_CODE" -eq 0 ]; then
    ok "Pytest prošel"
  else
    fail "Pytest selhal"
  fi
else
  warn "pytest není dostupný v PATH"
fi

section "13) NECHTĚNÉ SOUBORY / TECHNICKÝ DLUH"

PYC_COUNT="$(find . -type f -name '*.pyc' | wc -l | tr -d ' ')"
PYCACHE_COUNT="$(find . -type d -name '__pycache__' | wc -l | tr -d ' ')"
BAK_COUNT="$(find . -type f -name '*.bak_*' | wc -l | tr -d ' ')"
FIX_COUNT="$(find . -maxdepth 1 -type f \( -name 'fix_*.sh' -o -name 'apply_*.sh' -o -name '*patch*.sh' \) | wc -l | tr -d ' ')"

echo ".pyc count: $PYC_COUNT" | tee -a "$REPORT"
echo "__pycache__ count: $PYCACHE_COUNT" | tee -a "$REPORT"
echo "*.bak_* count: $BAK_COUNT" | tee -a "$REPORT"
echo "root fix/apply/patch scripts count: $FIX_COUNT" | tee -a "$REPORT"

if [ "$PYC_COUNT" -eq 0 ]; then
  ok "Žádné .pyc soubory"
else
  warn "Projekt obsahuje .pyc soubory"
fi

if [ "$PYCACHE_COUNT" -eq 0 ]; then
  ok "Žádné __pycache__ adresáře"
else
  warn "Projekt obsahuje __pycache__ adresáře"
fi

if [ "$BAK_COUNT" -le 5 ]; then
  ok "Nízký počet backup souborů"
else
  warn "Projekt obsahuje hodně backup souborů: $BAK_COUNT"
fi

if [ "$FIX_COUNT" -le 3 ]; then
  ok "Nízký počet jednorázových patch skriptů"
else
  warn "V rootu je hodně fix/apply/patch skriptů: $FIX_COUNT"
fi

section "14) GIT STAV"

if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
  git status --short | tee -a "$REPORT"

  DIRTY="$(git status --short | wc -l | tr -d ' ')"

  if [ "$DIRTY" -eq 0 ]; then
    ok "Git working tree je čistý"
  else
    warn "Git working tree není čistý: $DIRTY změn"
  fi

  echo | tee -a "$REPORT"
  git branch --show-current | sed 's/^/branch: /' | tee -a "$REPORT"
  git log -1 --oneline | sed 's/^/last commit: /' | tee -a "$REPORT"
else
  warn "Git není dostupný nebo projekt není git repo"
fi

section "15) CHECKSUM MANIFEST KRITICKÝCH SOUBORŮ"

if command -v sha256sum >/dev/null 2>&1; then
  MANIFEST="integrity_manifest_v2_$TS.sha256"

  sha256sum \
    app.py \
    lunch_platform/__init__.py \
    lunch_platform/templates/base.html \
    lunch_platform/templates/orders/index.html \
    lunch_platform/templates/orders/report.html \
    lunch_platform/templates/admin/dashboard.html \
    lunch_platform/static/app.js \
    lunch_platform/static/v4.css \
    lunch_platform/static/navy.css \
    lunch_platform/services/orders.py \
    lunch_platform/orders/routes.py \
    lunch_platform/admin/routes.py \
    > "$MANIFEST" 2>/dev/null || true

  ok "Checksum manifest vytvořen: $MANIFEST"
  cat "$MANIFEST" | tee -a "$REPORT"
else
  warn "sha256sum není dostupný"
fi

section "16) FINÁLNÍ VÝSLEDEK"

echo "PASS: $PASS" | tee -a "$REPORT"
echo "WARN: $WARN" | tee -a "$REPORT"
echo "FAIL: $FAIL" | tee -a "$REPORT"

echo | tee -a "$REPORT"
echo "Report uložen: $REPORT" | tee -a "$REPORT"

if [ "$FAIL" -gt 0 ]; then
  echo "[RESULT] FAIL - nejdřív oprav červené body." | tee -a "$REPORT"
  exit 1
fi

if [ "$WARN" -gt 0 ]; then
  echo "[RESULT] PASS WITH WARNINGS - aplikace může běžet, ale je tam technický dluh." | tee -a "$REPORT"
  exit 0
fi

echo "[RESULT] CLEAN PASS" | tee -a "$REPORT"
exit 0
