import pathlib


root = pathlib.Path(__file__).resolve().parents[1]
scope = {}
exec((root / "intake" / "work_order.py").read_text(encoding="utf-8"), scope)
case_scope = {}
exec((root / "checks" / "reschedule_case.py").read_text(encoding="utf-8"), case_scope)

order = scope["new_order"]("WO-17", "T-4", "2026-09-16")
assert scope["reschedule_order"](order, "2026-09-18")
assert case_scope["can_rebook"](order)
print("checks passed")
