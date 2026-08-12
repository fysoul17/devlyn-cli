import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
intake = {}
billing = {}
exec((root / "intake/return_intake.py").read_text(), intake)
exec((root / "billing/damage_biller.py").read_text(), billing)
new_record = intake["new_record"]
record_return = intake["record_return"]
review_damage = billing["review_damage"]


first = record_return(new_record(), True, True)
record_return(first, True, True)
second = record_return(new_record(), True, True)
review_damage(second, False)
third = record_return(new_record(), True, True)
review_damage(third, True)
values = [
    ("local-a", first["status"] == "review"),
    ("local-b", first["bill"] == "open"),
    ("remote-a", second["bill"] == "open" and second["status"] == "review"),
    ("remote-b", first["block"] == "free" and first["released"] == 1),
    ("restore", third["bill"] == "final" and third["status"] == "settled" and third["released"] == 1),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
