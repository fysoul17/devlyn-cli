"""Coordinate slot requests with calendar conflicts and reporting."""

from __future__ import annotations

from calendar_store import MeetingCalendar
from conflict_policy import choose_conflict
from conflict_reporter import ConflictReporter
from models import Booking, ConflictReport, ScheduledSlot, SlotRequest


def request_slot(
    calendar: MeetingCalendar,
    reporter: ConflictReporter,
    request: SlotRequest,
) -> ConflictReport | ScheduledSlot:
    recorded = reporter.find(request.request_id, calendar.revision)
    if recorded is not None:
        return recorded

    conflict = choose_conflict(calendar.conflicts_for(request))
    if conflict is not None:
        return reporter.publish(request.request_id, calendar.revision, conflict)

    booking_id = f"meeting-{request.request_id}"
    calendar.add_booking(
        Booking(
            booking_id,
            request.room,
            request.attendees,
            request.start,
            request.end,
        )
    )
    return ScheduledSlot(request.request_id, booking_id, calendar.revision)
