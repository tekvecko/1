from __future__ import annotations

import re
import unicodedata as _ud
from datetime import datetime, timedelta

MAX_NAME_LEN = 40
ALLOWED_DAYS = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek"]
DAYS_ORDER = {day: index for index, day in enumerate(ALLOWED_DAYS, start=1)}
DAYS_ORDER["Ostatní"] = 6


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_user_name(value: str) -> str:
    cleaned = normalize_spaces(value)
    cleaned = re.sub(r"[^0-9A-Za-zÁ-ž ._\-]", "", cleaned)
    return cleaned[:MAX_NAME_LEN].strip()


def normalize_person_name(value: str, *, max_len: int = 60) -> str:
    cleaned = normalize_spaces(value)
    cleaned = re.sub(r"[^0-9A-Za-zÁ-ž ._\-]", "", cleaned)
    return cleaned[:max_len].strip()


def normalize_email(value: str) -> str:
    return normalize_spaces(value).lower()[:120]


def name_to_initials(first_name: str | None, last_name: str | None) -> str:
    first = normalize_person_name(first_name or "")
    last = normalize_person_name(last_name or "")
    initials = ((first[:1] or "?") + (last[:1] or "?")).upper()
    return initials


def full_name_from_parts(first_name: str | None, last_name: str | None) -> str:
    return normalize_spaces(f"{first_name or ''} {last_name or ''}")


def clean_text_field(value: str, max_len: int) -> str:
    return normalize_spaces(value)[:max_len]


def dish_key(name: str) -> str:
    nd = "".join(c for c in _ud.normalize("NFD", (name or "").lower()) if _ud.category(c) != "Mn")
    return re.sub(r"\s+", " ", nd).strip()[:60]


def extract_price_cents(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).replace(",", ".")
    match = re.search(r"(\d+)(?:[.]?(\d{1,2}))?", text)
    if not match:
        return 0
    whole = int(match.group(1))
    frac = (match.group(2) or "0").ljust(2, "0")[:2]
    return whole * 100 + int(frac)


def format_price_czk(cents: int) -> str:
    return f"{cents // 100} Kč"


def get_week_dates() -> dict[str, str]:
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    return {day: (monday + timedelta(days=index)).strftime("%d.%m.") for index, day in enumerate(ALLOWED_DAYS)}
