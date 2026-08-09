"""Batch import for a bounded gradebook."""

from models import normalize_row
from validator import choose_issue


def import_rows(rows: list[dict], capacity: int) -> dict:
    normalized = [normalize_row(row) for row in rows]
    placed: list[str] = []
    rejected: list[dict] = []

    for arrival, row in enumerate(normalized):
        reason = choose_issue(row)
        if reason is not None:
            rejected.append({"arrival": arrival, "reason": reason})
            continue
        if len(placed) >= capacity:
            rejected.append({"arrival": arrival, "reason": "full"})
            continue
        placed.append(row["student"])

    return {"placed": placed, "rejected": rejected}
