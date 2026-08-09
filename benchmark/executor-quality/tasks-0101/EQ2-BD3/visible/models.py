"""Normalization for incoming DNS record changes."""


def normalize_change(change: dict) -> dict:
    return {
        "change": change.get("change"),
        "owner": change.get("owner"),
        "type": change.get("type"),
        "value": change.get("value"),
        "priority": change.get("priority", 0),
    }
