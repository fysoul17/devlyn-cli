from __future__ import annotations

import unittest

from models import Rejection
from reason_ranker import rank_rejections


class ReasonRankerTests(unittest.TestCase):
    def test_business_precedence_beats_arrival(self) -> None:
        ranked = rank_rejections(
            [Rejection(0, "closed"), Rejection(1, "bad_amount"), Rejection(2, "missing")]
        )
        self.assertEqual(
            ranked,
            (
                Rejection(1, "bad_amount"),
                Rejection(2, "missing"),
                Rejection(0, "closed"),
            ),
        )

    def test_arrival_breaks_equal_reason_ties(self) -> None:
        ranked = rank_rejections(
            [Rejection(4, "missing"), Rejection(1, "missing"), Rejection(3, "missing")]
        )
        self.assertEqual([item.source_index for item in ranked], [1, 3, 4])


if __name__ == "__main__":
    unittest.main()
