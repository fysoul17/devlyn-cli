"""Check the saved terminal payload only; native trace proves the child lifecycle."""
import json
import math
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
try:
    scenario = json.loads((root / "scenario.json").read_text())
    receipt = json.loads((root / "receipt.json").read_text())
    elapsed = receipt.get("elapsed_seconds") if isinstance(receipt, dict) else None
    passed = (isinstance(receipt, dict)
              and set(receipt) == {"event", "scenario", "marker", "elapsed_seconds"}
              and receipt["event"] == "gate-completed"
              and receipt["scenario"] == scenario["id"]
              and receipt["marker"] == scenario["marker"]
              and type(elapsed) in (int, float) and math.isfinite(elapsed)
              and elapsed >= scenario["wait_seconds"])
except (OSError, ValueError, TypeError):
    passed = False
print(json.dumps({"receipt_pass": passed}))
sys.exit(0 if passed else 1)
