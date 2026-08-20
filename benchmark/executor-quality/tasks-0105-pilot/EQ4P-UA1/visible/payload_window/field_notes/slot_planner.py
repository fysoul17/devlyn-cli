"""Plan payload slots for the next allocation board.

The planner records acceptance for a proposed slot and replacement.
"""


def plan_slot(allocation, replacement):
    return {"allocation": allocation, "replacement": replacement, "state": "acceptance"}
