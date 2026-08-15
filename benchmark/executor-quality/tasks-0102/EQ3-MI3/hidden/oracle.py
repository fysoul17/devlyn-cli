import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


ingester = load("ingester/reading_ingester.py")
tiering = load("billing/tierer.py")
checks = load("checks/misread_regression.py")
new_batch = ingester["new_batch"]
submit_correction = ingester["submit_correction"]
tier_invoice = tiering["tier_invoice"]
recomputes_once = checks["recomputes_once"]

READINGS = [
    {"meter_id": "M-17", "cumulative": 100, "recorded_at": "08:00"},
    {"meter_id": "M-17", "cumulative": 160, "recorded_at": "12:00"},
]
METER = "M-17"
SERIES = "series"
USAGE = "adjusted_usage"
VALID = "valid"

local = new_batch(READINGS)
accepted = submit_correction(local, METER, 130)

remote = new_batch(READINGS)
submit_correction(remote, METER, 130)
invoice = tier_invoice(remote)

repeat = new_batch(READINGS)
submit_correction(repeat, METER, 130)
submit_correction(repeat, METER, 130)
repeat_invoice = tier_invoice(repeat)
repeat_is_compensated = (
    repeat_invoice[VALID]
    and repeat_invoice[SERIES] == [100, 160]
    and repeat_invoice[USAGE] == 30
)

values = [
    ("local-a", accepted and len(local["readings"]) == 3),
    ("local-b", local["readings"][0]["cumulative"] == 100),
    ("remote-a", invoice[VALID] and invoice[SERIES] == [100, 160] and invoice[USAGE] == 30),
    ("remote-b", repeat_is_compensated and recomputes_once(repeat_invoice)),
    ("restore", invoice[VALID] and invoice[USAGE] == 30 and repeat_is_compensated and recomputes_once(repeat_invoice) and READINGS[1]["cumulative"] == 160),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
