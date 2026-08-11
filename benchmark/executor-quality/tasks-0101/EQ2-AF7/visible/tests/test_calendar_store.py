from __future__ import annotations

import unittest

from calendar_store import MeetingCalendar
from models import Booking, SlotRequest


class MeetingCalendarTests(unittest.TestCase):
    def test_add_booking_advances_revision(self) -> None:
        calendar = MeetingCalendar()

        calendar.add_booking(Booking("b1", "atlas", ("ava",), 540, 600))

        self.assertEqual(calendar.revision, 1)
        self.assertEqual(len(calendar.bookings), 1)

    def test_conflict_discovery_covers_person_and_room(self) -> None:
        calendar = MeetingCalendar((Booking("b2", "atlas", ("ava",), 540, 600),))

        conflicts = calendar.conflicts_for(SlotRequest("r1", "atlas", ("ava",), 555, 585))

        self.assertEqual([item.reason for item in conflicts], ["attendee", "room"])


if __name__ == "__main__":
    unittest.main()
