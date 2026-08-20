import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
sys.dont_write_bytecode = True
sys.path.insert(0, str(root))

from fitness_policy.editor.note_policy import apply_note_policy
from fitness_policy.services.policy_dispatch import contract_checks


def exercise(original, replacement, events):
    ledger = {
        "policy": original,
        "replacement": replacement,
        "seal": False,
        "allowed": True,
        "used": False,
        "events": list(events),
    }
    result = apply_note_policy(ledger)
    return ledger, result, original


cases = (exercise("P1", "Q1", ()), exercise("R2", "S2", ("rejected",)))
local_a = all(result == {"applied": False, "blocked": True} for _, result, _ in cases)
local_b = all(not ledger["allowed"] for ledger, _, _ in cases)
remote_a = all(contract_checks(ledger, original)[0] for ledger, _, original in cases)
remote_b = all(contract_checks(ledger, original)[1] for ledger, _, original in cases)
restore = local_a and local_b and remote_a and remote_b and all(
    ledger["policy"] == original and ledger["events"].count("rejected") == 1
    for ledger, _, original in cases
)
values = (
    ("local-a", local_a),
    ("local-b", local_b),
    ("remote-a", remote_a),
    ("remote-b", remote_b),
    ("restore", restore),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
