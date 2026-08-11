from __future__ import annotations

import unittest

from errors import StockFault
from models import Transfer
from stock_mover import move_batch
from stock_store import StockStore


def new_store() -> StockStore:
    return StockStore(
        {"east": {"A": 1}, "north": {"A": 8}, "west": {"B": 5}},
        {"east": {"A": 8}, "north": {"B": 8}},
    )


class StockMoverTests(unittest.TestCase):
    def test_successful_batch_changes_both_endpoints(self) -> None:
        store = new_store()
        result = move_batch(
            store,
            "ok",
            [Transfer("north", "east", "A", 3)],
        )

        self.assertEqual(result.moved, (Transfer("north", "east", "A", 3),))
        self.assertEqual(store.on_hand("north", "A"), 5)
        self.assertEqual(store.on_hand("east", "A"), 4)

    def test_transport_fault_restores_prior_completed_move(self) -> None:
        store = new_store()
        before = store.snapshot_bytes()

        with self.assertRaises(StockFault):
            move_batch(
                store,
                "fault",
                [
                    Transfer("north", "east", "A", 2),
                    Transfer("west", "north", "B", 1, fail_before_debit=True),
                ],
            )

        self.assertEqual(store.snapshot_bytes(), before)


if __name__ == "__main__":
    unittest.main()
