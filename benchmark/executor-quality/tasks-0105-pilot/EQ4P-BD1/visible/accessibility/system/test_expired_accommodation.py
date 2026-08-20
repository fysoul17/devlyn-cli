"""Accessibility coverage for an outdated arrangement.

The accessibility test asserts an expired accommodation reopens the proctor seat once.
"""


def expired_accommodation_reopens_seat(case):
    seat_snapshot = case.get("seat_snapshot")
    return (
        case["stale"]
        and case["seat_open"]
        and isinstance(seat_snapshot, dict)
        and case["seat_plan"] == seat_snapshot
        and case["seat_plan"]["seat_status"] == "available"
        and case["events"].count("reopened") == 1
    )


def test_expired_accommodation():
    plan = {"accommodation": "standard", "proctor": "room-proctor", "seat_status": "available"}
    case = {"stale": True, "seat_open": True, "seat_plan": plan, "seat_snapshot": dict(plan), "events": ["reopened"]}
    assert expired_accommodation_reopens_seat(case)


if globals().get("__name__") == "__main__":
    test_expired_accommodation()
