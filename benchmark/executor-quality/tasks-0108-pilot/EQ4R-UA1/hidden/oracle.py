import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
sys.dont_write_bytecode = True
sys.path.insert(0, str(root))

from payload_window.allocator.swap_allocator import apply_payload_swap
from payload_window.services.swap_dispatch import contract_checks


def exercise(original, replacement, notices):
    launch = {
        "allocation": original,
        "replacement": replacement,
        "hold": False,
        "range_ok": False,
        "slot_open": False,
        "notices": list(notices),
        "events": [],
    }
    apply_payload_swap(launch)
    launch["hold"] = True
    result = apply_payload_swap(launch)
    return launch, result, original


cases = (exercise("A1", "B1", ()), exercise("C2", "D2", ("hold",)))
local_a = all(result == {"accepted": False, "held": True} for _, result, _ in cases)
local_b = all(launch["hold"] and not launch["slot_open"] for launch, _, _ in cases)
remote_a = all(contract_checks(launch, original)[0] for launch, _, original in cases)
remote_b = all(contract_checks(launch, original)[1] for launch, _, original in cases)
restore = local_a and local_b and remote_a and remote_b and all(
    launch["notices"].count("hold") == 1 for launch, _, _ in cases
)
values = (
    ("local-a", local_a),
    ("local-b", local_b),
    ("remote-a", remote_a),
    ("remote-b", remote_b),
    ("restore", restore),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
