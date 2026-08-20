import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
sys.dont_write_bytecode = True
sys.path.insert(0, str(root))

from accommodation_allocator.allocator.accommodation_change import apply_accommodation_change
from accommodation_allocator.services.allocation_dispatch import contract_checks, seat_plan_for


def exercise(original, replacement, events):
    case = {
        "accommodation": original,
        "replacement": replacement,
        "seat_plan": seat_plan_for(original, "available"),
        "stale": False,
        "seat_open": True,
        "events": list(events),
    }
    apply_accommodation_change(case)
    case["stale"] = True
    result = apply_accommodation_change(case)
    return case, result, original


cases = (exercise("standard", "reader", ()), exercise("quiet", "reader", ("reopened",)))
local_a = all(result == {"allocated": False, "available": True} for _, result, _ in cases)
local_b = all(
    case["seat_open"] and case["seat_plan"]["seat_status"] == "available"
    for case, _, _ in cases
)
remote_a = all(contract_checks(case, original)[0] for case, _, original in cases)
remote_b = all(contract_checks(case, original)[1] for case, _, original in cases)
current_accommodations = (case["accommodation"] for case, _, _ in cases)
restore = local_a and local_b and remote_a and remote_b and all(
    accommodation == original
    and case["seat_plan"] == seat_plan_for(original, "available")
    and case["events"].count("reopened") == 1
    for accommodation, (case, _, original) in zip(current_accommodations, cases)
)
values = (
    ("local-a", local_a),
    ("local-b", local_b),
    ("remote-a", remote_a),
    ("remote-b", remote_b),
    ("restore", restore),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
