import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
fee_scope = {}
desk_scope = {}
exec((root / "circulation" / "fee_escalator.py").read_text(encoding="utf-8"), fee_scope)
exec((root / "loan_desk" / "renewal_intake.py").read_text(encoding="utf-8"), desk_scope)
record_overdue_fee = fee_scope["record_overdue_fee"]
renew_loan = desk_scope["renew_loan"]


def loan(pending):
    return {
        "due": 18,
        "fee_day": 10,
        "charged": False,
        "events": [],
        "hold": {"pending": pending, "slot": 4, "requeued": 0},
    }


normal = loan(False)
first = renew_loan(normal, 20, record_overdue_fee)
record_overdue_fee(normal, 23)
blocked = loan(True)
second = renew_loan(blocked, 20, record_overdue_fee)
renew_loan(blocked, 20, record_overdue_fee)
values = (
    ("local-a", first["accepted"] and bool(normal.get("renewed")) and normal["due"] == 34),
    ("local-b", not second["accepted"] and not blocked.get("renewed") and blocked["due"] == 18),
    ("remote-a", normal["fee_day"] == 10 and normal["events"] == [("late", 13)]),
    ("remote-b", blocked["due"] == 18 and blocked["hold"]["slot"] == 4 and blocked["hold"]["requeued"] == 0),
    ("restore", blocked["due"] == 18 and blocked["hold"]["slot"] == 4 and blocked["events"] == [("late", 10)]),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
