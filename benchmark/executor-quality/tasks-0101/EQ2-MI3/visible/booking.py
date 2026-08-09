"""Coordinate access policy and calendar placement."""

from access_policy import AccessPolicy
from calendar_placer import CalendarPlacer
from models import normalize_request
from priority import order_requests


def _view(booking):
    return {
        "id": booking.request_id,
        "room": booking.room,
        "start": booking.start_minute,
        "end": booking.end_minute,
    }


def schedule_day(requests, passes, room_zones, existing=()):
    normalized = [
        normalize_request(request, submitted_at)
        for submitted_at, request in enumerate(requests)
    ]
    policy = AccessPolicy(passes, room_zones)
    placer = CalendarPlacer(existing)
    confirmed = []
    denied = []
    unavailable = []

    for request in normalized:
        booking = placer.try_place(request)
        if booking is None:
            unavailable.append(request.request_id)
        else:
            confirmed.append(_view(booking))

    return {
        "confirmed": confirmed,
        "denied": denied,
        "unavailable": unavailable,
    }
