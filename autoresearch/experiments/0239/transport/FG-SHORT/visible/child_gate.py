"""One read-only part of a native foreground transport workload."""
import json
from pathlib import Path
import sys
import time

scenario = json.loads(Path(__file__).with_name("scenario.json").read_text())
if len(sys.argv) != 2 or sys.argv[1] not in {str(p["part"]) for p in scenario["parts"]}:
    raise SystemExit("Supply one registered part number")
part = next(p for p in scenario["parts"] if str(p["part"]) == sys.argv[1])
started = time.monotonic()
print(json.dumps({"event": "gate-started", "scenario": scenario["id"],
                  "part": part["part"], "wait_seconds": part["wait_seconds"]}), flush=True)
time.sleep(part["wait_seconds"])
print(json.dumps({"event": "gate-completed", "scenario": scenario["id"],
                  "part": part["part"], "marker": part["marker"],
                  "elapsed_seconds": time.monotonic() - started}), flush=True)
