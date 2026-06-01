from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange

@dataclass
class Occurrence:
    date: date
    label: str
    amount: float
    direction: str
    cashflow_id: int | None = None


def parse_day(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def add_months(anchor: date, months: int, preferred_day: int) -> date:
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(preferred_day, monthrange(year, month)[1])
    return date(year, month, day)


def next_date(start: date, idx: int, frequency: str) -> date:
    if frequency == "weekly":
        return start + timedelta(days=7 * idx)
    if frequency == "fortnightly":
        return start + timedelta(days=14 * idx)
    if frequency == "monthly":
        return add_months(start, idx, start.day)
    if frequency == "quarterly":
        return add_months(start, idx * 3, start.day)
    if frequency == "annually":
        return add_months(start, idx * 12, start.day)
    raise ValueError(f"Unsupported frequency: {frequency}")


def signed_amount(item) -> float:
    return float(item.amount) if item.direction == "income" else -float(item.amount)


def occurrences_for_item(item, start: date, end: date) -> list[Occurrence]:
    if not getattr(item, "active", True):
        return []
    item_start = parse_day(item.start_date)
    if item.kind == "one_off":
        if start <= item_start <= end:
            return [Occurrence(item_start, item.label, signed_amount(item), item.direction, getattr(item, "id", None))]
        return []
    if not item.frequency:
        return []

    result: list[Occurrence] = []
    idx = 0
    max_occ = item.end_occurrences if item.end_type == "occurrences" else None
    end_date = parse_day(item.end_date) if item.end_type == "end_date" and item.end_date else None
    while True:
        if max_occ is not None and idx >= max_occ:
            break
        occ_date = next_date(item_start, idx, item.frequency)
        if end_date and occ_date > end_date:
            break
        if occ_date > end:
            break
        if occ_date >= start:
            result.append(Occurrence(occ_date, item.label, signed_amount(item), item.direction, getattr(item, "id", None)))
        idx += 1
        if idx > 5000:
            raise RuntimeError("Recurring cashflow generated too many occurrences")
    return result


def occurrences_between(items, start: date, end: date) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for item in items:
        occurrences.extend(occurrences_for_item(item, start, end))
    return sorted(occurrences, key=lambda occ: (occ.date, occ.label))


def latest_anchor_on_or_before(anchors, target: date):
    eligible = [a for a in anchors if parse_day(a.date) <= target]
    if not eligible:
        return None
    return sorted(eligible, key=lambda a: (parse_day(a.date), getattr(a, "id", 0)))[-1]


def calculated_balance(anchors, items, target: date) -> tuple[float | None, object | None, list[Occurrence]]:
    anchor = latest_anchor_on_or_before(anchors, target)
    if not anchor:
        return None, None, []
    anchor_date = parse_day(anchor.date)
    occs = occurrences_between(items, anchor_date + timedelta(days=1), target)
    return float(anchor.amount) + sum(occ.amount for occ in occs), anchor, occs


def forecast(anchors, items, start: date, days: int = 60) -> dict:
    end = start + timedelta(days=days)
    all_occurrences = occurrences_between(items, start, end)
    by_date: dict[date, list[Occurrence]] = {}
    for occ in all_occurrences:
        by_date.setdefault(occ.date, []).append(occ)

    points = []
    for offset in range(days + 1):
        day = start + timedelta(days=offset)
        balance, anchor, occs_from_anchor = calculated_balance(anchors, items, day)
        daily = by_date.get(day, [])
        points.append({
            "date": day.isoformat(),
            "balance": balance,
            "anchor_id": getattr(anchor, "id", None) if anchor else None,
            "transactions": [{"label": o.label, "amount": o.amount, "direction": o.direction, "cashflow_id": o.cashflow_id} for o in daily],
        })
    valid = [p for p in points if p["balance"] is not None]
    peak = max(valid, key=lambda p: p["balance"]) if valid else None
    trough = min(valid, key=lambda p: p["balance"]) if valid else None
    return {"points": points, "peak": peak, "trough": trough}
