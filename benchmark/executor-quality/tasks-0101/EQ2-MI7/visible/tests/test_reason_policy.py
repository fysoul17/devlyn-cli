from __future__ import annotations

import unittest

from models import Rejection
from reason_policy import rank_rejections


class ReasonPolicyTests(unittest.TestCase):
    def test_business_priority_beats_detection_order(self) -> None:
        ranked = rank_rejections(
            (
                Rejection(0, "not_next"),
                Rejection(1, "paused"),
                Rejection(2, "full"),
            )
        )

        self.assertEqual(
            [(item.source_index, item.reason) for item in ranked],
            [(1, "paused"), (2, "full"), (0, "not_next")],
        )

    def test_detection_order_breaks_equal_reason_ties(self) -> None:
        ranked = rank_rejections(
            (
                Rejection(4, "full"),
                Rejection(1, "not_next"),
                Rejection(2, "full"),
            )
        )

        self.assertEqual(
            [(item.source_index, item.reason) for item in ranked],
            [(2, "full"), (4, "full"), (1, "not_next")],
        )


if __name__ == "__main__":
    unittest.main()
