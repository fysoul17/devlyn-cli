import unittest

from calendar_placer import CalendarPlacer
from models import RoomRequest


class CalendarPlacerTests(unittest.TestCase):
    def test_overlapping_request_is_not_placed(self):
        placer = CalendarPlacer()
        first = RoomRequest("first", "sam", "atlas", 10, 20, 1, 0)
        conflict = RoomRequest("conflict", "sam", "atlas", 15, 25, 2, 1)

        self.assertIsNotNone(placer.try_place(first))
        self.assertIsNone(placer.try_place(conflict))


if __name__ == "__main__":
    unittest.main()
