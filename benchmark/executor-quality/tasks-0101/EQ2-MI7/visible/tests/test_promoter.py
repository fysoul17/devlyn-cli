from __future__ import annotations

import unittest

from duplicate_log import DuplicateEntryLog
from fixtures import full_board, open_board
from models import PromotionRequest
from promoter import submit_promotion


class PromoterTests(unittest.TestCase):
    def test_exact_success_retry_changes_board_once(self) -> None:
        board = open_board()
        log = DuplicateEntryLog()
        request = PromotionRequest("r2", "ava")

        first = submit_promotion(board, log, request)
        second = submit_promotion(board, log, request)

        self.assertEqual(first, second)
        self.assertEqual(board.queue, ("ben", "cy"))
        self.assertEqual(board.roster, ("ava",))
        self.assertEqual(len(log.outcomes()), 1)

    def test_changed_retry_body_reuses_first_rejection(self) -> None:
        board = full_board(paused=("cy",))
        log = DuplicateEntryLog()

        first = submit_promotion(board, log, PromotionRequest("r3", "ava"))
        second = submit_promotion(board, log, PromotionRequest("r3", "cy"))

        self.assertEqual(first.reason, "full")
        self.assertEqual(second, first)
        self.assertEqual(board.queue, ("ava", "ben", "cy"))
        self.assertEqual(board.roster, ("zoe",))
        self.assertEqual(len(log.outcomes()), 1)


if __name__ == "__main__":
    unittest.main()
