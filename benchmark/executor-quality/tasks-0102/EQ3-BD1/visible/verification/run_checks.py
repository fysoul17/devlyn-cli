"""Run the fixture's visible gate-close scenario."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path, namespace):
    exec(path.read_text(encoding="utf-8"), namespace)


gate = {}
balance = {}
checks = {}
load(ROOT / "gate" / "vehicle_checkin.py", gate)
load(ROOT / "stowage" / "deck_load_balancer.py", balance)
load(ROOT / "verification" / "bumped_vehicle_test.py", checks)
manifest = gate["close_gate"](gate["open_manifest"](), "truck-8")
report = balance["recompute_reserve"](manifest)
print({"state": manifest["vehicles"]["truck-8"]["state"], "report": report})
