"""Interval calendar state and conflict discovery."""

from __future__ import annotations

from collections.abc import Iterable

from models import Booking, Conflict, SlotRequest


OPEN_MINUTE = 8 * 60
CLOSE_MINUTE = 18 * 60


def overlaps(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end


class MeetingCalendar:
    def __init__(self, bookings: Iterable[Booking] = ()) -> None:
        self._bookings: list[Booking] = []
        self._revision = 0
        for booking in bookings:
            self.add_booking(booking)

    @property
    def bookings(self) -> tuple[Booking, ...]:
        return tuple(self._bookings)

    @property
    def revision(self) -> int:
        return self._revision

    def add_booking(self, booking: Booking) -> None:
        self._bookings.append(booking)
        self._revision += 1

    def conflicts_for(self, request: SlotRequest) -> tuple[Conflict, ...]:
        conflicts: list[Conflict] = []
        if request.start < OPEN_MINUTE or request.end > CLOSE_MINUTE or request.start >= request.end:
            conflicts.append(Conflict(len(conflicts), "outside", "hours"))

        requested_attendees = set(request.attendees)
        for booking in self._bookings:
            if not overlaps(request.start, request.end, booking.start, booking.end):
                continue
            if requested_attendees.intersection(booking.attendees):
                conflicts.append(Conflict(len(conflicts), "attendee", booking.booking_id))
            if request.room == booking.room:
                conflicts.append(Conflict(len(conflicts), "room", booking.booking_id))
        return tuple(conflicts)
