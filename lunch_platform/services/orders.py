from __future__ import annotations

import re
from collections import Counter, defaultdict

from ..core.db import account_full_name, execute, query, log_event
from ..core.utils import ALLOWED_DAYS, dish_key
from ..domain.workflow import can_transition

EMOJI_MAP = {
    "kuřec": "🍗", "vepřov": "🥩", "hověz": "🥩", "řízek": "🥩", "guláš": "🍲",
    "těstovin": "🍝", "špaget": "🍝", "rizot": "🍚", "rýž": "🍚", "polévk": "🥣",
    "vývar": "🥣", "krém": "🥣", "ryb": "🐟", "losos": "🐟", "salát": "🥗",
    "zelenin": "🥦", "brokolic": "🥦", "brambor": "🥔", "sýr": "🧀", "burger": "🍔",
    "pizz": "🍕", "palačink": "🥞", "dezert": "🍰", "koláč": "🥧", "buchtičk": "🧁",
    "vejce": "🍳", "párk": "🌭", "knedlík": "🥟", "omáčk": "🍛",
}


def get_emoji(name: str) -> str:
    low = (name or '').lower()
    for key, value in EMOJI_MAP.items():
        if key in low:
            return value
    return '🍽️'


def grouped_menu():
    rows = query("SELECT * FROM menu ORDER BY CASE day WHEN 'Pondělí' THEN 1 WHEN 'Úterý' THEN 2 WHEN 'Středa' THEN 3 WHEN 'Čtvrtek' THEN 4 WHEN 'Pátek' THEN 5 ELSE 99 END, id")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["day"]].append(row)
    return dict(grouped)


def get_user_orders(account_id: int):
    return query(
        """
        SELECT o.*, COALESCE(m.day, o.day) AS menu_day
        FROM orders o
        LEFT JOIN menu m ON m.id=o.dish_id
        WHERE o.created_by_account_id=?
        ORDER BY o.created_at DESC
        """,
        (account_id,),
    )


def get_user_selected_map(account_id: int):
    rows = query("SELECT day, dish_id FROM orders WHERE created_by_account_id=? AND status IN ('draft','submitted')", (account_id,))
    return {row["day"]: row["dish_id"] for row in rows}




def get_day_status_map(account_id: int):
    rows = query("SELECT day, status FROM orders WHERE created_by_account_id=?", (account_id,))
    status_by_day = {day: 'none' for day in ALLOWED_DAYS}
    for row in rows:
        day = row['day']
        status = row['status']
        if status == 'paid':
            status_by_day[day] = 'paid'
        elif status in {'draft', 'submitted', 'locked', 'sent_to_vendor', 'delivered', 'invoiced'} and status_by_day.get(day) != 'paid':
            status_by_day[day] = 'selected'
        elif status == 'cancelled' and day not in status_by_day:
            status_by_day[day] = 'none'
    return status_by_day

def get_order_counts() -> dict[int, int]:
    return {row['dish_id']: row['cnt'] for row in query("SELECT dish_id, COUNT(*) AS cnt FROM orders WHERE dish_id IS NOT NULL AND status NOT IN ('cancelled') GROUP BY dish_id")}


def get_rating_counts() -> dict[str, int]:
    return {row['dish_key']: row['cnt'] for row in query("SELECT dish_key, COUNT(*) AS cnt FROM ratings WHERE score=1 GROUP BY dish_key")}


def get_user_rated_keys(account_id: int) -> set[str]:
    return {row['dish_key'] for row in query("SELECT dish_key FROM ratings WHERE account_id=?", (account_id,))}


def get_user_recommendations(account_id: int) -> list[str]:
    rows = query(
        "SELECT dish_name_snapshot FROM orders WHERE created_by_account_id=? AND status NOT IN ('cancelled') ORDER BY created_at DESC LIMIT 30",
        (account_id,),
    )
    words: list[str] = []
    for row in rows:
        clean = re.sub(r"\(.*?\)", "", row['dish_name_snapshot'] or '').lower()
        words.extend(re.findall(r"[a-záčďéěíňóřšťůúýž]{5,}", clean))
    return [item for item, _count in Counter(words).most_common(4)]


def _extract_allergen_numbers(name: str) -> list[str]:
    if '(' not in name or ')' not in name:
        return []
    tail = name[name.rfind('('):]
    return re.findall(r"\d+", tail)


def build_menu_view_model(account_id: int, allergens_csv: str = ''):
    menu = grouped_menu()
    selected = get_user_selected_map(account_id)
    day_status = get_day_status_map(account_id)
    order_counts = get_order_counts()
    rating_counts = get_rating_counts()
    rated_keys = get_user_rated_keys(account_id)
    recommendations = set(get_user_recommendations(account_id))
    user_allergens = {item.strip() for item in (allergens_csv or '').split(',') if item.strip()}

    total_cents = 0
    cart_items = []
    menu_view: dict[str, list[dict]] = {}

    for day, dishes in menu.items():
        day_list = []
        for dish in dishes:
            dk = dish_key(dish['dish_name'])
            dish_allergens = set(_extract_allergen_numbers(dish['dish_name']))
            is_selected = selected.get(day) == dish['id']
            if is_selected:
                total_cents += dish['price_cents']
                cart_items.append({
                    'day': day,
                    'dish_name': dish['dish_name'],
                    'price_text': dish['price_text'],
                    'emoji': get_emoji(dish['dish_name']),
                })
            recommended = any(word in dish['dish_name'].lower() for word in recommendations)
            safe = not bool(user_allergens.intersection(dish_allergens))
            popularity = order_counts.get(dish['id'], 0)
            thumbs = rating_counts.get(dk, 0)
            rated = dk in rated_keys
            day_list.append({
                'id': dish['id'],
                'day': day,
                'dish_name': dish['dish_name'],
                'price_text': dish['price_text'],
                'price_cents': dish['price_cents'],
                'emoji': get_emoji(dish['dish_name']),
                'selected': is_selected,
                'recommended': recommended,
                'safe': safe,
                'popularity': popularity,
                'thumbs': thumbs,
                'rated': rated,
                'allergen_numbers': sorted(dish_allergens, key=lambda x: int(x)),
                'manual': False,
                'source_line': '',
                'continued_lines': [],
            })
        menu_view[day] = day_list

    return {
        'menu': menu_view,
        'selected_by_day': selected,
        'cart_items': cart_items,
        'cart_count': len(cart_items),
        'cart_total_cents': total_cents,
        'cart_total_text': f"{total_cents // 100} Kč",
        'menu_days': list(menu.keys()),
        'day_status_by_day': {day: day_status.get(day, 'none') for day in menu.keys()},
        'order_counts': order_counts,
        'rating_counts': rating_counts,
        'rated_keys': rated_keys,
    }


def place_order(account, day: str, dish_id: int):
    if day not in ALLOWED_DAYS:
        raise ValueError('Unsupported day')
    dish = query('SELECT * FROM menu WHERE id=?', (dish_id,), one=True)
    if not dish:
        raise ValueError('Dish not found')
    if dish['day'] != day:
        raise ValueError('For each day you can choose only one lunch from that day menu')
    execute(
        """
        INSERT INTO orders(created_by_account_id, day, dish_id, status, dish_name_snapshot, price_snapshot_text, price_snapshot_cents)
        VALUES (?, ?, ?, 'draft', ?, ?, ?)
        ON CONFLICT(created_by_account_id, day)
        DO UPDATE SET dish_id=excluded.dish_id,
                      status='draft',
                      dish_name_snapshot=excluded.dish_name_snapshot,
                      price_snapshot_text=excluded.price_snapshot_text,
                      price_snapshot_cents=excluded.price_snapshot_cents,
                      cancelled_at=NULL
        """,
        (account['id'], day, dish_id, dish['dish_name'], dish['price_text'], dish['price_cents']),
    )
    log_event('order_selected', account_id=account['id'], actor=account_full_name(account), role=account['role'], target=day, detail=dish['dish_name'])
    return current_state(account['id'])


def cancel_order(account, day: str):
    order = query('SELECT * FROM orders WHERE created_by_account_id=? AND day=?', (account['id'], day), one=True)
    if not order:
        raise ValueError('Order not found')
    if order['status'] in {'locked', 'sent_to_vendor', 'delivered', 'invoiced', 'paid'}:
        raise ValueError('Order can no longer be cancelled')
    execute("UPDATE orders SET status='cancelled', cancelled_at=CURRENT_TIMESTAMP WHERE id=?", (order['id'],))
    log_event('order_cancelled', account_id=account['id'], actor=account_full_name(account), role=account['role'], target=day)
    return current_state(account['id'])


def rate_dish(account, dish_name: str):
    execute(
        'INSERT OR IGNORE INTO ratings(account_id, dish_key, score) VALUES (?, ?, 1)',
        (account['id'], dish_key(dish_name)),
    )
    log_event('dish_rated', account_id=account['id'], actor=account_full_name(account), role=account['role'], detail=dish_name)


def current_state(account_id: int):
    state = build_menu_view_model(account_id)
    return {
        'selected_by_day': state['selected_by_day'],
        'cart_items': state['cart_items'],
        'cart_count': state['cart_count'],
        'cart_total_cents': state['cart_total_cents'],
        'cart_total_text': state['cart_total_text'],
        'menu_days': state['menu_days'],
        'day_status_by_day': state['day_status_by_day'],
    }
