from __future__ import annotations

import unittest

from models import PromotionRequest, Rejection
from waitlist import PromotionBoard


class PromotionBoardTests(unittest.TestCase):
    def test_validation_reports_every_applicable_reason(self) -> None:
        board = PromotionBoard(
            ("ava", "ben"),
            1,
            roster=("zoe",),
            paused=("ben",),
        )

        self.assertEqual(
            board.rejections_for(PromotionRequest("r4", "ben")),
            (
                # Rule positions are stable inputs to reason selection.
                Rejection(0, "paused"),
                Rejection(1, "full"),
                Rejection(2, "not_next"),
            ),
        )

    def test_promotion_moves_only_the_front_candidate(self) -> None:
        board = PromotionBoard(("ava", "ben"), 2)

        board.promote_next("ava")

        self.assertEqual(board.queue, ("ben",))
        self.assertEqual(board.roster, ("ava",))


if __name__ == "__main__":
    unittest.main()
