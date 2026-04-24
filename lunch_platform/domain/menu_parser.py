from __future__ import annotations

import re
import unicodedata as _ud

from lunch_platform.core.utils import ALLOWED_DAYS, extract_price_cents, format_price_czk, normalize_spaces

DEFAULT_PRICE_CENTS = 15000

_DAY_ALIASES = {
    "Pondělí": {"pondeli", "pondělí", "po", "pond"},
    "Úterý": {"utery", "úterý", "ut", "út"},
    "Středa": {"streda", "středa", "st", "str"},
    "Čtvrtek": {"ctvrtek", "čtvrtek", "ct", "čt"},
    "Pátek": {"patek", "pátek", "pa", "pá"},
}

DAY_RE = re.compile(
    r"^(pondělí|pondeli|po|pond|úterý|utery|út|ut|středa|streda|st|str|čtvrtek|ctvrtek|čt|ct|pátek|patek|pá|pa)"
    r"(?:\s*[:\-.])?"
    r"(?:\s+\d{1,2}\s*[./]\s*\d{1,2}(?:\s*[./]\s*\d{2,4})?\.?) *"
    r"(?:\s*[-–—:]\s*)?$",
    re.IGNORECASE,
)
DISH_START_RE = re.compile(
    r"^(\d{1,2}[.)]|Minutka:|Sal[áa]t:|Dezert:|Vegetari[aá]nsk[eé]:|Veggie:|Fit:)",
    re.IGNORECASE,
)
SOUP_START_RE = re.compile(r"^(?:0[,.]?\d*\s*l\b|Pol[eé]vka:)\s*(.+)$", re.IGNORECASE)
PRICE_RE = re.compile(
    r"(?<!\d)(\d{2,3})(?:[,.]\d{1,2})?\s*(?:,-\s*)?(?:kč|kc|czk|eur)?(?!\d)",
    re.IGNORECASE,
)
WEIGHT_RE = re.compile(r"\b\d{2,4}\s*g\b", re.IGNORECASE)
TRAILING_PUNCT_RE = re.compile(r"[\s,;./-]+$")


def _no_diacritics(value: str) -> str:
    return "".join(c for c in _ud.normalize("NFD", value or "") if _ud.category(c) != "Mn")


def _detect_day(line: str) -> str | None:
    candidate = normalize_spaces(line).rstrip(":.- ")
    if not candidate:
        return None
    nd = _no_diacritics(candidate.lower())
    nd = re.sub(r"\s+\d{1,2}\s*[./]\s*\d{1,2}(?:\s*[./]\s*\d{2,4})?\.?", "", nd).strip()
    nd = nd.rstrip(":.- ")
    if len(nd.split()) != 1:
        return None
    for canonical, aliases in _DAY_ALIASES.items():
        if nd in aliases:
            return canonical
    if DAY_RE.match(candidate):
        token = nd.split()[0] if nd.split() else nd
        for canonical, aliases in _DAY_ALIASES.items():
            if token in aliases:
                return canonical
    return None


def _sanitize_line(line: str) -> str:
    line = line.replace("•", " ").replace("●", " ").replace("\xa0", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _is_noise(line: str) -> bool:
    if not line:
        return True
    nd = _no_diacritics(line.lower())
    noisy_bits = (
        "www.", "http", "tel", "telefon", "provozni", "vydej", "adresa", "oteviraci", "objednav",
        "jidelnicek", "poledni menu", "denni menu", "menu na tyden", "rozvoz", "kontakt", "rezervace",
    )
    if any(bit in nd for bit in noisy_bits) and not DISH_START_RE.match(line) and not SOUP_START_RE.match(line):
        return True
    if re.fullmatch(r"[\d\s./-]+", line):
        return True
    return False


def _looks_suspicious(line: str) -> bool:
    if not line or _is_noise(line):
        return False
    if len(line) < 4:
        return True
    if line.count("(") != line.count(")"):
        return True
    if re.search(r"\b\d{4,}\b", line):
        return True
    if not re.search(r"[A-Za-zÁ-ž]", line):
        return True
    return False


def _extract_price_and_body(line: str) -> tuple[str, int, bool, str]:
    best = None
    best_score = -1
    for match in PRICE_RE.finditer(line):
        try:
            value = int(match.group(1))
        except ValueError:
            continue
        if not 10 <= value <= 999:
            continue
        token = match.group(0).lower()
        score = 0
        if any(currency in token for currency in ("kč", "kc", "czk", "eur")):
            score += 10
        if value >= 50:
            score += 3
        if match.end() >= len(line.rstrip()) - 1:
            score += 2
        if score >= best_score:
            best = match
            best_score = score
    if not best:
        return line, DEFAULT_PRICE_CENTS, False, ""
    body = f"{line[:best.start()]} {line[best.end():]}".strip()
    body = normalize_spaces(body)
    return body, extract_price_cents(best.group(0)), True, best.group(0)


def _clean_dish_body(body: str) -> str:
    body = normalize_spaces(body)
    body = WEIGHT_RE.sub("", body)
    body = re.sub(r"^(\d{1,2}[.)])\s*", "", body)
    body = re.sub(r"^(Minutka:|Sal[áa]t:|Dezert:|Vegetari[aá]nsk[eé]:|Veggie:|Fit:)\s*", "", body, flags=re.IGNORECASE)
    body = normalize_spaces(body)
    body = TRAILING_PUNCT_RE.sub("", body)
    return body.strip()


def _parse_day_blocks(text: str) -> tuple[dict[str, list[tuple[int, str]]], list[dict[str, object]]]:
    blocks: dict[str, list[tuple[int, str]]] = {}
    preamble_lines: list[dict[str, object]] = []
    current_day: str | None = None
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _sanitize_line(raw)
        if not line:
            continue
        maybe_day = _detect_day(line)
        if maybe_day:
            current_day = maybe_day
            blocks.setdefault(current_day, [])
            continue
        if not current_day:
            preamble_lines.append({"line_no": line_no, "text": line})
            continue
        blocks.setdefault(current_day, []).append((line_no, line))
    return blocks, preamble_lines


def analyze_menu_text(text: str) -> dict[str, object]:
    blocks, preamble_lines = _parse_day_blocks(text)
    parsed_items: list[dict[str, object]] = []
    skipped_lines: list[dict[str, object]] = []
    suspicious_lines: list[dict[str, object]] = []
    missing_price_items: list[dict[str, object]] = []
    recognized_days: list[str] = []
    day_sections: list[dict[str, object]] = []

    for entry in preamble_lines:
        if _is_noise(str(entry["text"])):
            skipped_lines.append({**entry, "reason": "header_noise"})
        else:
            suspicious_lines.append({**entry, "reason": "content_before_first_day"})

    for day in ALLOWED_DAYS:
        raw_entries = blocks.get(day, [])
        logical_entries: list[dict[str, object]] = []
        day_skipped: list[dict[str, object]] = []
        day_suspicious: list[dict[str, object]] = []

        for line_no, line in raw_entries:
            if _is_noise(line):
                item = {"day": day, "line_no": line_no, "text": line, "reason": "noise"}
                skipped_lines.append(item)
                day_skipped.append(item)
                continue

            if DISH_START_RE.match(line) or SOUP_START_RE.match(line):
                logical_entries.append({"line_no": line_no, "text": line, "continuations": []})
                continue

            if logical_entries:
                logical_entries[-1]["text"] = f"{logical_entries[-1]['text']} {line}".strip()
                logical_entries[-1]["continuations"].append({"line_no": line_no, "text": line})
                continue

            item = {"day": day, "line_no": line_no, "text": line, "reason": "unattached_line"}
            skipped_lines.append(item)
            day_skipped.append(item)
            if _looks_suspicious(line):
                sus = {**item, "reason": "suspicious_unattached_line"}
                suspicious_lines.append(sus)
                day_suspicious.append(sus)

        if logical_entries:
            recognized_days.append(day)

        parsed_preview: list[dict[str, object]] = []
        for entry in logical_entries:
            line = str(entry["text"])
            soup_match = SOUP_START_RE.match(line)
            source_line = int(entry["line_no"])
            if soup_match:
                body, price_cents, had_price, price_source = _extract_price_and_body(soup_match.group(1))
                dish_name = _clean_dish_body(body)
                if not dish_name:
                    suspect = {"day": day, "line_no": source_line, "text": line, "reason": "empty_soup_after_parse"}
                    suspicious_lines.append(suspect)
                    day_suspicious.append(suspect)
                    continue
                full_name = f"Polévka: {dish_name}"
            else:
                if not DISH_START_RE.match(line):
                    suspect = {"day": day, "line_no": source_line, "text": line, "reason": "unrecognized_logical_line"}
                    suspicious_lines.append(suspect)
                    day_suspicious.append(suspect)
                    continue
                body, price_cents, had_price, price_source = _extract_price_and_body(line)
                full_name = _clean_dish_body(body)
                if not full_name:
                    suspect = {"day": day, "line_no": source_line, "text": line, "reason": "empty_dish_after_parse"}
                    suspicious_lines.append(suspect)
                    day_suspicious.append(suspect)
                    continue

            if not had_price:
                warning = {
                    "day": day,
                    "line_no": source_line,
                    "text": line,
                    "dish_name": full_name,
                    "fallback_price_text": format_price_czk(price_cents),
                }
                missing_price_items.append(warning)

            item = {
                "day": day,
                "dish_name": full_name,
                "price_cents": int(price_cents),
                "price_text": format_price_czk(int(price_cents)),
                "source_line": source_line,
                "source_text": line,
                "had_explicit_price": bool(had_price),
                "price_source": price_source,
                "continued_lines": entry.get("continuations", []),
            }
            parsed_items.append(item)
            parsed_preview.append(item)

        day_sections.append({
            "day": day,
            "recognized": day in recognized_days,
            "raw_lines": [{"line_no": ln, "text": txt} for ln, txt in raw_entries],
            "logical_lines": [
                {
                    "line_no": int(e["line_no"]),
                    "text": str(e["text"]),
                    "continuation_count": len(e.get("continuations", [])),
                }
                for e in logical_entries
            ],
            "parsed_items": parsed_preview,
            "skipped_lines": day_skipped,
            "suspicious_lines": day_suspicious,
        })

    missing_days = [day for day in ALLOWED_DAYS if day not in recognized_days]
    summary = {
        "recognized_day_count": len(recognized_days),
        "parsed_item_count": len(parsed_items),
        "missing_price_count": len(missing_price_items),
        "skipped_line_count": len(skipped_lines),
        "suspicious_line_count": len(suspicious_lines),
    }
    return {
        "items": parsed_items,
        "recognized_days": recognized_days,
        "missing_days": missing_days,
        "missing_price_items": missing_price_items,
        "skipped_lines": skipped_lines,
        "suspicious_lines": suspicious_lines,
        "preamble_lines": preamble_lines,
        "day_sections": day_sections,
        "summary": summary,
    }


def parse_menu_text(text: str):
    report = analyze_menu_text(text)
    return [
        (item["day"], item["dish_name"], int(item["price_cents"]))
        for item in report["items"]
    ]
