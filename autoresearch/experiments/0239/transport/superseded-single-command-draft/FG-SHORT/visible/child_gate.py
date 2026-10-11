"""Read-only transport workload: print a start event and one terminal result."""
import json
from pathlib import Path
import time

scenario = json.loads(Path(__file__).with_name("scenario.json").read_text())
started = time.monotonic()
print(json.dumps({"event": "gate-started", "scenario": scenario["id"],
                  "wait_seconds": scenario["wait_seconds"]}), flush=True)
time.sleep(scenario["wait_seconds"])
print(json.dumps({"event": "gate-completed", "scenario": scenario["id"],
                  "marker": scenario["marker"],
                  "elapsed_seconds": time.monotonic() - started}), flush=True)
