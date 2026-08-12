"""Simple counters for a daily report."""


def count_by_kind(events):
    return {kind: sum(item["kind"] == kind for item in events) for kind in {item["kind"] for item in events}}
