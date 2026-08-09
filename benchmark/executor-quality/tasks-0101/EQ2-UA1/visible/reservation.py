"""Batch reservation coordinator."""

from hold_queue import rank_requests
from models import normalize_request
from seat_map import SeatMap


def reserve_batch(requests: list[dict], seats: list[str]) -> dict:
    normalized = [normalize_request(request) for request in requests]
    seat_map = SeatMap(seats)
    accepted: list[str] = []
    rejected: list[str] = []

    for request in rank_requests(normalized):
        complete = True
        for seat in request["seats"]:
            if not seat_map.hold(request["id"], seat):
                complete = False
                break
        if not complete:
            rejected.append(request["id"])
            continue
        seat_map.commit(request["id"])
        accepted.append(request["id"])

    return {
        "accepted": accepted,
        "rejected": rejected,
        "assignments": seat_map.assignments(),
        "available": seat_map.available(),
    }
