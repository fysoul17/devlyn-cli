"""Record arrangement changes and expose downstream checks."""

from accessibility.system.test_expired_accommodation import expired_accommodation_reopens_seat
from proctor_scheduling.seats.accommodation_consumer import proctor_plan_tracks_accommodation, seat_plan_for


def record_allocation(case, previous):
    case["events"].append(("allocation", previous))


def contract_checks(case, original):
    return (
        proctor_plan_tracks_accommodation(case, original),
        expired_accommodation_reopens_seat(case),
    )
