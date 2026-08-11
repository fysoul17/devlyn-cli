"""Small calendars used by examples and tests."""

from __future__ import annotations

from calendar_store import MeetingCalendar
from models import Booking, SlotRequest


def room_conflict_calendar() -> MeetingCalendar:
    return MeetingCalendar((Booking("b-room", "atlas", ("zoe",), 9 * 60, 10 * 60),))


def attendee_conflict_calendar() -> MeetingCalendar:
    return MeetingCalendar((Booking("b-person", "cedar", ("ava",), 10 * 60, 11 * 60),))


def room_request(request_id: str = "r-room") -> SlotRequest:
    return SlotRequest(request_id, "atlas", ("ava",), 9 * 60, 10 * 60)


def attendee_request(request_id: str = "r-person") -> SlotRequest:
    return SlotRequest(request_id, "birch", ("ava",), 10 * 60, 11 * 60)
