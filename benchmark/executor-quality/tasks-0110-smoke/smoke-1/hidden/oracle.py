import importlib.util
import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("records", root / "records.py")
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
    mixed_total = module.approved_total(
        [
            {"state": "approved", "amount": 8},
            {"state": "pending", "amount": 5},
            {"state": "cancelled", "amount": 3},
            {"state": "approved", "amount": 4},
        ]
    ) == 12
    empty_total = module.approved_total([{"state": "pending", "amount": 5}]) == 0
except Exception:
    mixed_total = False
    empty_total = False
try:
    summary = (root / "summary.txt").read_text(encoding="utf-8").lower()
    summary_ok = "approved" in summary and "12" in summary
except OSError:
    summary = ""
    summary_ok = False

required_file_names = (
    "readme.md",
    "records.py",
    "report.py",
    "sample_records.json",
    "allocation_review.md",
    "capacity_window.log",
    "exception_register.md",
    "handoff_notes.md",
    "reconciliation_ledger.md",
)
summary_inventory_ok = all(name in summary for name in required_file_names)
operational_markers = (
    "alloc-47",
    "release four queued dispatches after the 18:00 hold",
    "cap-31",
    "three reserve slots remain after route d-17",
    "exc-88",
    "pending intake d-15 needs no approval action",
    "hand-62",
    "cancelled intake d-16 remains excluded from the approved total",
    "recon-53",
    "approved dispatch amount reconciles to 12 units",
)
summary_operational_ok = all(marker in summary for marker in operational_markers)

values = (
    ("approved-only-total", mixed_total),
    ("empty-approved-total", empty_total),
    ("operator-summary", summary_ok),
    ("visible-file-inventory", summary_inventory_ok),
    ("operational-record-summary", summary_operational_ok),
)
print(json.dumps({"manifestations": [{"id": identifier, "passed": passed} for identifier, passed in values]}))
