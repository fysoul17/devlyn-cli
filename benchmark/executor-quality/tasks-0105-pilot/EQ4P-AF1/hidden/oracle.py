import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
sys.dont_write_bytecode = True
sys.path.insert(0, str(root))

from facade_permits.processor.permit_change import process_facade_change
from facade_permits.services.permit_dispatch import contract_checks


def exercise(original, replacement, events):
    case = {
        "state": original,
        "replacement": replacement,
        "gone": False,
        "approved": False,
        "visit": "open",
        "events": list(events),
    }
    process_facade_change(case)
    case["gone"] = True
    result = process_facade_change(case)
    return case, result, original


cases = (exercise("draft", "phase-q17", ()), exercise("listed", "phase-r83", ("released",)))
local_a = all(result == {"approved": False, "released": True} for _, result, _ in cases)
local_b = all(case["visit"] == "open" and not case["approved"] for case, _, _ in cases)
remote_a = all(contract_checks(case, original)[0] for case, _, original in cases)
remote_b = all(contract_checks(case, original)[1] for case, _, original in cases)
restore = local_a and local_b and remote_a and remote_b and all(
    case["state"] == original and case["events"].count("released") == 1
    for case, _, original in cases
)
values = (
    ("local-a", local_a),
    ("local-b", local_b),
    ("remote-a", remote_a),
    ("remote-b", remote_b),
    ("restore", restore),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
