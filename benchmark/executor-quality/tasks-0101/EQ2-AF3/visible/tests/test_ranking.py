import unittest

from ranking import order_rows


class RankingTests(unittest.TestCase):
    def test_source_order_is_preserved_without_reordering(self) -> None:
        rows = [{"rank": 3}, {"rank": 3}]
        self.assertEqual([index for index, _ in order_rows(rows)], [0, 1])


if __name__ == "__main__":
    unittest.main()
