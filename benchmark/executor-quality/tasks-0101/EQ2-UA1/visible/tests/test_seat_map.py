import unittest

from seat_map import SeatMap


class SeatMapTests(unittest.TestCase):
    def test_release_returns_tentative_seats(self) -> None:
        seat_map = SeatMap(["A", "B"])
        self.assertTrue(seat_map.hold("r1", "A"))
        seat_map.release("r1")
        self.assertEqual(seat_map.available(), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
