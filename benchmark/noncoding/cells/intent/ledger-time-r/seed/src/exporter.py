from __future__ import annotations

from datetime import datetime


def format_last_seen(value: datetime) -> str:
    """Render an aware timestamp for the CSV export."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("last_seen must include a timezone")
    return value.isoformat(timespec="seconds")


def export_row(account: str, last_seen: datetime) -> dict[str, str]:
    return {"account": account, "last_seen": format_last_seen(last_seen)}
