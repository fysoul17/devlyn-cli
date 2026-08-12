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
expire(three, "corn")
released = three["reserved"]
restored = three["stock"]["fizz"]
refund = three["refunds"]
four = reserve(make())
expire(four, "fizz")
expire(four, "fizz")
spoilage = four["spoilage"]
reserve(four)
remaining = four["stock"]["corn"]
hold = four["reserved"]
refund_once = four["refunds"]
values = (
    ("local-a", corn == 1 and fizz == 0),
    ("local-b", booked == 1),
    ("remote-a", released == 0 and restored == 1 and refund == 1),
    ("remote-b", spoilage == 1 and remaining == 2 and hold == 0),
    ("restore", not available(four) and refund_once == 1 and four["stock"]["fizz"] == 0),
)
print(json.dumps({"manifestations": [{"id": role, "passed": passed} for role, passed in values]}))
