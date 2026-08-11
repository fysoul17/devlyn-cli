from __future__ import annotations

import unittest

from duplicate_log import DuplicateEntryLog
from models import PromotionOutcome, PromotionRequest


class DuplicateEntryLogTests(unittest.TestCase):
    def test_exact_retry_finds_recorded_outcome(self) -> None:
        log = DuplicateEntryLog()
        request = PromotionRequest("r1", "ava")
        outcome = PromotionOutcome("r1", "ava", "rejected", "full")

        log.append(request, outcome)

        self.assertEqual(log.find(request), outcome)
        self.assertEqual(log.outcomes(), (outcome,))


if __name__ == "__main__":
    unittest.main()
