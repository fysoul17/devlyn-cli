import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
gate = {}
balance = {}
checks = {}
exec((root / "gate" / "vehicle_checkin.py").read_text(encoding="utf-8"), gate)
exec((root / "stowage" / "deck_load_balancer.py").read_text(encoding="utf-8"), balance)
exec((root / "verification" / "bumped_vehicle_test.py").read_text(encoding="utf-8"), checks)

make_manifest = gate["open_manifest"]
close_gate = gate["close_gate"]
first = close_gate(make_manifest(), "truck-8")
second = close_gate(first, "truck-8")
reserve_key = "reserve_units"
booking_key = "booking_units"
report = balance["recompute_reserve"](second)
position_kept = checks["is_position_kept"](second, "truck-8")
fare_once = checks["fare_charged_once"](second, "truck-8")
values = (
    ("local-a", first["vehicles"]["truck-8"]["state"] == "bumped"),
    ("local-b", fare_once and len(second["bumped"]) == 1),
    ("remote-a", report[reserve_key] == second[booking_key]["truck-8"]),
    ("remote-b", position_kept),
    ("restore", report[reserve_key] == second[booking_key]["truck-8"] and position_kept and fare_once),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
