from __future__ import annotations

import unittest

from conflict_reporter import ConflictReporter
from fixtures import room_conflict_calendar, room_request
from models import SlotRequest
from scheduler import request_slot


class SchedulerTests(unittest.TestCase):
    def test_rejected_retry_reuses_report_in_same_snapshot(self) -> None:
        calendar = room_conflict_calendar()
        reporter = ConflictReporter()
        request = room_request()

        first = request_slot(calendar, reporter, request)
        second = request_slot(calendar, reporter, request)

        self.assertEqual(first, second)
        self.assertEqual(len(reporter.reports(request.request_id)), 1)
        self.assertEqual(reporter.notification_count, 1)
        self.assertEqual(len(calendar.bookings), 1)

    def test_clear_slot_creates_one_booking(self) -> None:
        from calendar_store import MeetingCalendar

        calendar = MeetingCalendar()
        reporter = ConflictReporter()
        request = SlotRequest("r-open", "atlas", ("ava",), 720, 780)

        outcome = request_slot(calendar, reporter, request)

        self.assertEqual(outcome.booking_id, "meeting-r-open")
        self.assertEqual(len(calendar.bookings), 1)
        self.assertEqual(reporter.notification_count, 0)


if __name__ == "__main__":
    unittest.main()
