import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


intake = load("intake/work_order.py")
dispatcher = load("dispatch/tenant_window_dispatcher.py")
regression = load("checks/no_access_regression.py")


def prepared():
    order = intake["new_order"]("WO-17", "T-4", "2026-09-16")
    first = intake["record_no_access"](order, 110)
    dispatcher["book_contractor_window"](order)
    return order, first


local = intake["new_order"]("WO-17", "T-4", "2026-09-16")
local_result = intake["reschedule_order"](local, "2026-09-18")

remote, first_result = prepared()
intake["reschedule_order"](remote, "2026-09-18")
second_result = intake["record_no_access"](remote, 125)
dispatcher["book_contractor_window"](remote)

repeated, _ = prepared()
intake["reschedule_order"](repeated, "2026-09-18")
intake["record_no_access"](repeated, 125)
dispatcher["book_contractor_window"](repeated)
intake["record_no_access"](repeated, 150)


values = [
    ("local-a", local_result is True),
    ("local-b", local["status"] == "scheduled" and local["requested" + "_date"] == "2026-09-18"),
    ("remote-a", first_result is False and second_result is True and dispatcher["has_second" + "_window"](remote)),
    ("remote-b", regression["noaccess" + "_clock" + "_has" + "_continuity"](remote, 100) and regression["waived_once"](remote)),
    ("restore", regression["noaccess" + "_clock" + "_has" + "_continuity"](repeated, 100) and regression["waived_once"](repeated) and len(repeated["no" + "_access" + "_visits"]) == 3),
]
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
