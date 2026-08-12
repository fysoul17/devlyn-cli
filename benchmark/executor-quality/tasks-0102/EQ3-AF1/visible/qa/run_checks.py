"""Run the symptom-level intake checks from the task ticket."""

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
scope = {}
exec((ROOT / "intake" / "hold_intake.py").read_text(encoding="utf-8"), scope)

board = scope["new_board"]()
unit = scope["reserve_next"](board)
order = board["orders"][0]

assert unit["state"] == "reserved"
assert order["state"] == "held" and order["unit"] == unit["tag"]
print("intake checks passed")
