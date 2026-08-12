import json
import pathlib
import sys


scope = {}
root = pathlib.Path(sys.argv[1])
exec((root / "editor" / "combo_editor.py").read_text(encoding="utf-8"), scope)
make = scope["open_shift"]
reserve = scope["reserve_combo"]
expire = scope["expire_component"]
available = scope["combo_available"]

one = reserve(make())
corn = one["stock"]["corn"]
fizz = one["stock"]["fizz"]
two = reserve(make())
booked = two["reserved"]
three = reserve(make())
expire(three, "fizz")
released = three["reserved"]
restored = three["stock"]["corn"]
four = reserve(make())
expire(four, "fizz")
expire(four, "fizz")
spoilage = four["spoilage"]
five = reserve(make())
expire(five, "fizz")
remaining = five["stock"]["corn"]
hold = five["reserved"]
values = (
    ("local-a", corn == 1 and fizz == 0),
    ("local-b", booked == 1),
    ("remote-a", released == 0 and restored == 2),
    ("remote-b", spoilage == 1),
    ("restore", not available(five) and remaining == 2 and hold == 0),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
