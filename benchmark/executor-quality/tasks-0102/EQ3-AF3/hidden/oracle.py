import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


desk = load("desk/loan_out.py")
gate = load("conservation/treatment_gate.py")
new_loan = desk["new_loan"]
dispatch = desk["dispatch"]
close_transfer = desk["close_transfer"]

local = new_loan(True, False, "west-14")
local_sent = dispatch(local)

blocked = new_loan(True, True, "south-03")
blocked_sent = dispatch(blocked)
clear = gate["is_clear_for_movement"](blocked)

returned = new_loan(True, False, "north-09")
home = returned["home_position"]
occupied_before_dispatch = returned["position"] == home
was_sent = dispatch(returned)
vacated_at_dispatch = returned["position"] is None
first_close = close_transfer(returned)
position = returned["position"]
coverage_open = returned["coverage_open"]
releases = returned["coverage_releases"]
second_close = close_transfer(returned)
after_releases = returned["coverage_releases"]

values = [
    ("local-a", local_sent is True),
    ("local-b", local["state"] == "in_transit"),
    ("remote-a", not clear and blocked_sent is False),
    ("remote-b", was_sent and first_close and returned["state"] == "closed" and position == home and not coverage_open),
    ("restore", occupied_before_dispatch and vacated_at_dispatch and position == home and second_close and releases == 1 and after_releases == 1),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
