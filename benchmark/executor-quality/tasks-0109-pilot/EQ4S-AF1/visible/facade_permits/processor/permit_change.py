"""Process a provisional facade change after a routine review."""

from facade_permits.services.permit_dispatch import record_change


def process_facade_change(case):
    previous = case["state"]
    case["state"] = case["replacement"]
    record_change(case, previous)
    case["approved"] = True
    case["visit"] = "held"
    return {"approved": True, "released": False}
