import unittest

from availability import intervals_overlap


class AvailabilityTests(unittest.TestCase):
    def test_adjacent_intervals_do_not_overlap(self):
        self.assertFalse(intervals_overlap(10, 20, 20, 30))
        self.assertTrue(intervals_overlap(10, 21, 20, 30))


if __name__ == "__main__":
    unittest.main()
