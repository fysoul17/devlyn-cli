"""Run the symptom-level checks described by the intake ticket."""

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
scope = {}
exec((ROOT / "intake" / "adoption_intake.py").read_text(encoding="utf-8"), scope)

case = scope["open_case"]("A-1", True, False, None, "R-1", 25)
assert scope["adopt"](case, "R-2") is True
assert case["state"] == "adopted"
print("adoption intake checks passed")
