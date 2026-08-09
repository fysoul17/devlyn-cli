import unittest

from release_pool import ReleasePool


class ReleasePoolTests(unittest.TestCase):
    def test_collects_returns_from_earlier_arrivals(self) -> None:
        pool = ReleasePool()
        pool.deposit(0, ["P1"])
        self.assertEqual(pool.collect_before(1), ["P1"])


if __name__ == "__main__":
    unittest.main()
