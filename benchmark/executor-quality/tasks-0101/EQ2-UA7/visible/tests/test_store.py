from __future__ import annotations

import unittest

from models import Transfer
from stock_store import StockStore


class StockStoreTests(unittest.TestCase):
    def test_completed_move_can_be_undone_byte_for_byte(self) -> None:
        store = StockStore(
            {"east": {"A": 1}, "north": {"A": 8}},
            {"east": {"A": 8}},
        )
        before = store.snapshot_bytes()
        transfer = Transfer("north", "east", "A", 3)

        store.debit(transfer)
        store.credit(transfer)
        store.undo(transfer)

        self.assertEqual(store.snapshot_bytes(), before)

    def test_destination_policy_distinguishes_lock_and_capacity(self) -> None:
        store = StockStore(
            {"cold": {"B": 1}, "east": {"A": 4}, "north": {"A": 8}},
            {"cold": {"B": 8}, "east": {"A": 5}},
            blocked=("cold",),
        )

        self.assertEqual(
            store.destination_issue(Transfer("north", "cold", "B", 2)),
            "blocked",
        )
        self.assertEqual(
            store.destination_issue(Transfer("north", "east", "A", 2)),
            "full",
        )


if __name__ == "__main__":
    unittest.main()
