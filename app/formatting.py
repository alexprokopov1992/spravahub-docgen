from datetime import datetime

MONTHS_UA = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
}


def _parse(value: str):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def date_short(value: str) -> str:
    d = _parse(value)
    return d.strftime("%d.%m.%Y") if d else ""


def date_short_year(value: str) -> str:
    d = _parse(value)
    return f"{d.strftime('%d.%m.%Y')} року" if d else ""


def date_long(value: str) -> str:
    d = _parse(value)
    return f"{d.day:02d} {MONTHS_UA[d.month]} {d.year} року" if d else ""


def date_signature(value: str) -> str:
    d = _parse(value)
    return f"«{d.day:02d}» {MONTHS_UA[d.month]} {d.year} року" if d else ""


def period_short(start: str, end: str) -> str:
    if not start and not end:
        return ""
    if start and end:
        return f"{date_short(start)} року по {date_short(end)} року"
    return date_short_year(start or end)


def period_long(start: str, end: str) -> str:
    if not start and not end:
        return ""
    if start and end:
        return f"{date_long(start)} по {date_long(end)}"
    return date_long(start or end)


def years_phrase(raw: str) -> str:
    years = [x.strip() for x in (raw or "").replace(";", ",").split(",") if x.strip()]
    return ", ".join(f"{y} рік" for y in years)


def years_at_jan_1(raw: str) -> str:
    years = [x.strip() for x in (raw or "").replace(";", ",").split(",") if x.strip()]
    return ", ".join(f"на 01.01.{y} року" for y in years)
