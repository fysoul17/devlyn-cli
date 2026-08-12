import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


clerk = load("clerk/amendment_intake.py")
calendar = load("calendar/hearing_scheduler.py")
docket_ops = load("docket/continuance.py")
checks = load("checks/continuance_rollback_test.py")
new_docket = clerk["new_docket"]
file_amendment = clerk["file_amendment"]
notice_is_sufficient = calendar["notice_is_sufficient"]
start_continuance = docket_ops["start_continuance"]
rollback_continuance = docket_ops["rollback_continuance"]
continuance_rollback_holds = checks["continuance_rollback_holds"]


local = new_docket(14, 10)
local_result = file_amendment(local, {"caption": "revision", "submitted_on": 12})

scheduled = new_docket(14, 10)
file_amendment(scheduled, {"caption": "opening", "submitted_on": 7})
file_amendment(scheduled, {"caption": "revision", "submitted_on": 12})

restored = new_docket(14, 10)
file_amendment(restored, {"caption": "opening", "submitted_on": 7})
before = list(restored["filings"])
restore_result = file_amendment(restored, {"caption": "revision", "submitted_on": 12})
start_continuance(restored, 21)
rollback_continuance(restored)

values = [
    ("local-a", local_result is False),
    ("local-b", local["status"] == "rejected" and local["trail"] == ["rejected"]),
    ("remote-a", notice_is_sufficient(scheduled, 4)),
    ("remote-b", continuance_rollback_holds(new_docket, file_amendment, start_continuance, rollback_continuance)),
    ("restore", not restore_result and notice_is_sufficient(restored, 4) and restored["filings"] == before),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
