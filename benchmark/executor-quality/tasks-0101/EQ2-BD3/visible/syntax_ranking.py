"""Dependent rejection ranking for record-applier output."""

from errors import ERROR_PRIORITY
from record_applier import apply_changes


def build_ranked_plan(changes: list[dict]) -> dict:
    raw = apply_changes(changes)
    rejected: list[dict] = []
    for item in raw["rejected"]:
        reason = min(item["issues"], key=ERROR_PRIORITY.get)
        rejected.append({"source": item["source"], "reason": reason})
    rejected.sort(key=lambda item: (ERROR_PRIORITY[item["reason"]], item["source"]))
    return {
        "placed": [item["change"] for item in raw["placed"]],
        "rejected": rejected,
    }
