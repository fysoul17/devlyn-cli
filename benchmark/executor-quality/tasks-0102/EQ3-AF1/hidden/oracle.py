import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(*parts):
    scope = {}
    exec((root.joinpath(*parts)).read_text(encoding="utf-8"), scope)
    return scope


intake = load("intake", "hold_intake.py")
reserver = load("matching", "crossmatch_reserver.py")
release = load("qa", "expiry_release.py")

local = intake["new_board"]()
selected = intake["reserve_next"](local)
local_order = local["orders"][0]

wrong_pass = intake["new_board"]()
wrong_unit = intake["reserve_next"](wrong_pass)
intake["flag_expiry_for_reconciliation"](
    wrong_pass, wrong_unit["tag"], "antibody-reconciliation"
)
intake["sweep_expiry_reconciliation"](wrong_pass, "handoff-reconciliation")

remote = intake["new_board"]()
remote_unit = intake["reserve_next"](remote)
intake["flag_expiry_for_reconciliation"](
    remote, remote_unit["tag"], "antibody-reconciliation"
)
intake["sweep_expiry_reconciliation"](remote, "antibody-reconciliation")

restored = intake["new_board"]()
restored_unit = intake["reserve_next"](restored)
intake["flag_expiry_for_reconciliation"](
    restored, restored_unit["tag"], "antibody-reconciliation"
)
intake["flag_expiry_for_reconciliation"](
    restored, restored_unit["tag"], "antibody-reconciliation"
)
intake["sweep_expiry_reconciliation"](restored, "antibody-reconciliation")
intake["sweep_expiry_reconciliation"](restored, "antibody-reconciliation")

values = (
    ("local-a", selected["state"] == "reserved"),
    ("local-b", local_order["state"] == "held" and local_order["unit"] == selected["tag"]),
    (
        "remote-a",
        reserver["held_orders"](wrong_pass) == ["ORDER-17"]
        and not reserver["held_orders"](remote),
    ),
    ("remote-b", release["ready_for_match"](remote, "ORDER-17")),
    (
        "restore",
        release["ready_for_match"](restored, "ORDER-17")
        and release["isolated_once"](restored, "UNIT-1")
        and not reserver["held_orders"](restored),
    ),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
