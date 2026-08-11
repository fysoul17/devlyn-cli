from __future__ import annotations

import unittest

from conflict_policy import rank_conflicts
from models import Conflict


class ConflictPolicyTests(unittest.TestCase):
    def test_reason_priority_precedes_source_order(self) -> None:
        ranked = rank_conflicts(
            (
                Conflict(0, "room", "b1"),
                Conflict(1, "outside", "hours"),
                Conflict(2, "attendee", "b2"),
            )
        )

        self.assertEqual(
            [(item.source_index, item.reason) for item in ranked],
            [(1, "outside"), (2, "attendee"), (0, "room")],
        )

    def test_source_order_breaks_equal_reason_ties(self) -> None:
        ranked = rank_conflicts(
            (
                Conflict(5, "attendee", "b5"),
                Conflict(2, "room", "b2"),
                Conflict(1, "attendee", "b1"),
            )
        )

        self.assertEqual(
            [(item.source_index, item.reason) for item in ranked],
            [(1, "attendee"), (5, "attendee"), (2, "room")],
        )


if __name__ == "__main__":
    unittest.main()
