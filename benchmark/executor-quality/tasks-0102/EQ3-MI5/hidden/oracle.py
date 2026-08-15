import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root))
sys.dont_write_bytecode = True

from checks.partial_fill_test import partial_fill_debits_once, released_units_match
from intake.refill_intake import new_refill_state, submit_refill
from interactions.pending_gate import interaction_screen


def fresh():
    return new_refill_state(["lisinopril"], 10)


local = fresh()
first_local = submit_refill(local, "RX-101", "naproxen", 3)
repeat_local = submit_refill(local, "RX-101", "naproxen", 3)

remote = fresh()
first_remote = submit_refill(remote, "RX-101", "naproxen", 3)
screen_blocks_second = not interaction_screen(remote, "ibuprofen")
second_remote = submit_refill(remote, "RX-102", "ibuprofen", 4)

restored = fresh()
first_restored = submit_refill(restored, "RX-101", "naproxen", 3)
repeat_restored = submit_refill(restored, "RX-101", "naproxen", 3)
failed_one = submit_refill(restored, "RX-102", "ibuprofen", 4)
failed_two = submit_refill(restored, "RX-102", "ibuprofen", 4)
release_rows = [row for row in restored["release_log"] if row["fill_id"] == "RX-102"]

values = [
    ("local-a", first_local["accepted"] is True and local["units_left"] == 7),
    ("local-b", repeat_local.get("duplicate") is True and len(local["debits"]) == 1),
    ("remote-a", first_remote["accepted"] is True and screen_blocks_second and second_remote["accepted"] is False and remote["units_left"] == 7),
    ("remote-b", partial_fill_debits_once(remote, "RX-101", "RX-102") and released_units_match(remote, "RX-102", 4)),
    ("restore", first_restored["accepted"] is True and repeat_restored.get("duplicate") is True and failed_one["accepted"] is False and failed_two["accepted"] is False and restored["units_left"] == 7 and len(restored["debits"]) == 1 and len(release_rows) == 2 and all(row["units"] == 4 for row in release_rows) and not interaction_screen(restored, "ibuprofen")),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
