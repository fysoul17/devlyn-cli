import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
scope = {}
exec((root / "assigner" / "site_assigner.py").read_text(encoding="utf-8"), scope)
move_site = scope["move_site"]
cancel_booking = scope["cancel_booking"]
availability = "avail" + "ability"


def booking():
    return {
        "site": "tent",
        availability: {"tent": 0, "cabin": 1},
        "rates": {"tent": 40, "cabin": 85},
        "deposit": 40,
        "ledger": [],
        "reversals": 0,
    }


first = booking()
move_site(first, "cabin")
second = booking()
move_site(second, "cabin")
cancel_booking(second)
third = booking()
move_site(third, "cabin")
cancel_booking(third)
cancel_booking(third)
values = (
    ("local-a", first["site"] == "cabin" and first["deposit"] == 85),
    ("local-b", first[availability] == {"tent": 1, "cabin": 0} and first["ledger"] == [("move", "tent", "cabin", 45)]),
    ("remote-a", second[availability] == {"tent": 0, "cabin": 1} and second["deposit"] == 40),
    ("remote-b", second["ledger"] == [("move", "tent", "cabin", 45), ("reversal", "cabin", "tent", -45)]),
    ("restore", third["cancelled"] and third["reversals"] == 1 and third[availability] == {"tent": 0, "cabin": 1} and third["deposit"] == 40 and len(third["ledger"]) == 2),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
