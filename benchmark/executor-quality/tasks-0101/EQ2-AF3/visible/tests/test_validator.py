import unittest

from validator import choose_issue


class ValidatorTests(unittest.TestCase):
    def test_out_of_range_score_is_rejected(self) -> None:
        row = {"student": "s1", "score": 101, "rank": 2}
        self.assertEqual(choose_issue(row), "score")


if __name__ == "__main__":
    unittest.main()
