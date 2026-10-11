"""Validate saved part payloads only; the native trace proves the lifecycle."""
import json
import math
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
try:
    scenario = json.loads((root / "scenario.json").read_text())
    receipt = json.loads((root / "receipt.json").read_text())
    results = receipt.get("parts") if isinstance(receipt, dict) else None
    passed = (isinstance(receipt, dict) and set(receipt) == {"parts"}
              and isinstance(results, list) and len(results) == len(scenario["parts"]))
    if passed:
        for result, part in zip(results, scenario["parts"]):
            elapsed = result.get("elapsed_seconds") if isinstance(result, dict) else None
            passed = (passed and isinstance(result, dict)
                      and set(result) == {"event", "scenario", "part", "marker", "elapsed_seconds"}
                      and result["event"] == "gate-completed"
                      and result["scenario"] == scenario["id"]
                      and type(result["part"]) is int and result["part"] == part["part"]
                      and result["marker"] == part["marker"]
                      and type(elapsed) in (int, float) and math.isfinite(elapsed)
                      and elapsed >= part["wait_seconds"])
except (OSError, ValueError, TypeError):
    passed = False
print(json.dumps({"receipt_pass": passed}))
sys.exit(0 if passed else 1)
