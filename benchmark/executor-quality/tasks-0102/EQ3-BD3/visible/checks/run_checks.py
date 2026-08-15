"""Run the focused booking-desk checks without external dependencies."""

import pathlib


def load(relative):
    namespace = {}
    exec((pathlib.Path(__file__).parents[1] / relative).read_text(), namespace)
    return namespace


booking = load("booking/cancellation.py")
seat = load("checks/seat_counter_test.py")
session = booking["new_session"](4, 16)
for member in ("ada", "bo", "cam"):
    booking["add_member"](session, member)
booking["cancel_booking"](session, "ada", 18)
if not seat["seats_match"](session):
    raise SystemExit("seat display is not balanced")
print("booking checks passed")
