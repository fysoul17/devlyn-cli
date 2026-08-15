import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


booking = load("booking/cancellation.py")
desk = load("booking/desk.py")
pay = load("payroll/instructor_payroll.py")
seat = load("checks/seat_counter_test.py")
policy = load("checks/late_cancel_policy.py")


def prepared():
    session = booking["new_session"](4, 16)
    for member in ("ada", "bo", "cam"):
        booking["add_member"](session, member)
    booking["finalize_attendance"](session)
    return session


local = prepared()
local_result = booking["cancel_booking"](local, "ada", 18)

pay_session = prepared()
before_names = list(pay_session["settled"])
booking["cancel_booking"](pay_session, "ada", 18)

award_session = prepared()
booking["cancel_booking"](award_session, "ada", 18)

combined = prepared()
combined_before = list(combined["settled"])
first = booking["cancel_booking"](combined, "ada", 18)
second = booking["cancel_booking"](combined, "ada", 18)

values = [
    ("local-a", local_result and desk["open_seats"](local) == 2),
    ("local-b", local_result and seat["seats_match"](local)),
    ("remote-a", pay["pay_count"](pay_session) == 3 and list(pay_session["settled"]) == before_names),
    ("remote-b", policy["credit_once"](award_session, "ada")),
    ("restore", first and not second and seat["seats_match"](combined) and pay["pay_count"](combined) == 3 and list(combined["settled"]) == combined_before and policy["credit_once"](combined, "ada")),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
