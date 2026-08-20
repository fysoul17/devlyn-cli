"""Consumer rules for a remote examination accommodation.

The proctor-scheduling consumer assigns proctors from the current approved
accommodation and requires the prior accommodation and seat plan to return
after expiry.
"""


PROCTORS = {
    "standard": "room-proctor",
    "quiet": "quiet-room-proctor",
    "reader": "reader-support-proctor",
}


def seat_plan_for(accommodation, seat_status):
    return {
        "accommodation": accommodation,
        "proctor": PROCTORS[accommodation],
        "seat_status": seat_status,
    }


def proctor_plan_tracks_accommodation(case, original):
    expected = seat_plan_for(original, "available")
    return (
        case["stale"]
        and case.get("prior_accommodation") == original
        and case["accommodation"] == original
        and case.get("seat_snapshot") == expected
        and case["seat_plan"] == expected
    )
