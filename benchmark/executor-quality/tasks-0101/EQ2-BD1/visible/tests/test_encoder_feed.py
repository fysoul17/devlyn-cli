import unittest

from feed_order import rank_submissions


class EncoderFeedTests(unittest.TestCase):
    def test_rank_submissions_is_stable(self) -> None:
        submissions = [
            {"id": "low", "asset": "a", "priority": 1},
            {"id": "first", "asset": "b", "priority": 4},
            {"id": "second", "asset": "c", "priority": 4},
        ]
        self.assertEqual(
            [item["id"] for item in rank_submissions(submissions)],
            ["first", "second", "low"],
        )


if __name__ == "__main__":
    unittest.main()
