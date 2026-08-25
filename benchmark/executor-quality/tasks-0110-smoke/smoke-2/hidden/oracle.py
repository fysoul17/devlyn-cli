import importlib.util
import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("queue_fixture", root / "queue.py")
module = importlib.util.module_from_spec(spec)
cases = [
    {"id": "case-bravo", "status": "open", "deadline": "2026-08-26"},
    {"id": "case-closed", "status": "closed", "deadline": "2026-08-24"},
    {"id": "case-alpha", "status": "open", "deadline": "2026-08-25"},
    {"id": "case-charlie", "status": "open", "deadline": "2026-08-28"},
]
try:
    spec.loader.exec_module(module)
    ordered = module.ordered_open_cases(cases)
    earliest_first = [case["id"] for case in ordered] == ["case-alpha", "case-bravo", "case-charlie"]
    closed_excluded = all(case["status"] == "open" for case in ordered)
except Exception:
    earliest_first = False
    closed_excluded = False
try:
    summary = (root / "summary.txt").read_text(encoding="utf-8").lower()
    summary_ok = "earliest" in summary and "case-alpha" in summary
except OSError:
    summary_ok = False

values = (
    ("earliest-open-first", earliest_first),
    ("closed-case-excluded", closed_excluded),
    ("operator-summary", summary_ok),
)
print(json.dumps({"manifestations": [{"id": identifier, "passed": passed} for identifier, passed in values]}))
