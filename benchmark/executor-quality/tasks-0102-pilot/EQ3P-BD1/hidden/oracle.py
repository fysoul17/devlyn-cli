import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
assignments = {}
water = {}
exec((root / "assignments" / "plot_assigner.py").read_text(encoding="utf-8"), assignments)
exec((root / "water" / "share_scheduler.py").read_text(encoding="utf-8"), water)
make = assignments["open_season"]
abandon = assignments["abandon_plot"]
schedule = water["schedule"]

one = abandon(make(), "north")
available = one["plots"]["north"]["available"]
count = one["released"]
two = abandon(make(), "north")
shares = schedule(two)
empty = not shares
three = abandon(make(), "north")
waiting = three["waitlist"]
draw = three["lottery"]
four = abandon(make(), "north")
again = abandon(four, "north")
once = again["released"]
stable = again["waitlist"]
values = (
    ("local-a", available),
    ("local-b", count == 1),
    ("remote-a", empty),
    ("remote-b", waiting == ["bo", "cy"] and draw == ["north"]),
    ("restore", once == 1 and stable == ["bo", "cy"]),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
