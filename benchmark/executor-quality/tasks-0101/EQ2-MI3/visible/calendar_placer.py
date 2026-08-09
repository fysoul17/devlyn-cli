"""Mutable calendar placement isolated from access decisions."""

from availability import room_is_free
from models import Booking


class CalendarPlacer:
    def __init__(self, existing=()):
        self._bookings = list(existing)

    def try_place(self, request):
        if not room_is_free(self._bookings, request):
            return None
        booking = Booking(
            request.request_id,
            request.room,
            request.start_minute,
            request.end_minute,
        )
        self._bookings.append(booking)
        return booking
