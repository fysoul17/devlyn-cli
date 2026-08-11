from __future__ import annotations

import unittest

from discrepancy_reporter import DiscrepancyReporter
from models import Discrepancy


def issue(source_index: int, reason: str) -> Discrepancy:
    return Discrepancy(source_index, reason, "from", "to", "A")


class ReporterTests(unittest.TestCase):
    def test_business_reason_precedence_beats_source_order(self) -> None:
        ranked = DiscrepancyReporter().rank(
            [issue(0, "full"), issue(1, "bad_qty"), issue(2, "blocked")]
        )
        self.assertEqual([item.reason for item in ranked], ["bad_qty", "blocked", "full"])

    def test_source_order_breaks_equal_reason_ties(self) -> None:
        ranked = DiscrepancyReporter().rank(
            [issue(4, "blocked"), issue(3, "bad_qty"), issue(1, "blocked")]
        )
        self.assertEqual([item.source_index for item in ranked], [3, 1, 4])


if __name__ == "__main__":
    unittest.main()
