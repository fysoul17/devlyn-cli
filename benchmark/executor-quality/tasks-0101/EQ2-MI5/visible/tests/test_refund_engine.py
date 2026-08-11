from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from errors import RefundBatchError, StoreFault
from models import ReturnRequest
from refund_engine import process_returns
from return_store import ReturnStore


class RefundEngineTests(unittest.TestCase):
    def make_store(self, root: str) -> ReturnStore:
        return ReturnStore.create(
            Path(root) / "orders.json",
            {"open": 1000, "done": 500},
            closed=("done",),
        )

    def test_successful_batch_records_refunds(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            result = process_returns(store, "batch-a", [ReturnRequest("open", 250)])
            self.assertEqual(result.refunded_order_ids, ("open",))
            self.assertEqual(store.view()["completed_batches"], ["batch-a"])

    def test_store_fault_restores_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            before = store.snapshot_bytes()
            with self.assertRaises(StoreFault):
                process_returns(
                    store,
                    "batch-b",
                    [ReturnRequest("open", 250, fail_after_write=True)],
                )
            self.assertEqual(store.snapshot_bytes(), before)

    def test_rejected_batch_uses_reason_ranker(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = self.make_store(root)
            with self.assertRaises(RefundBatchError) as raised:
                process_returns(
                    store,
                    "batch-c",
                    [ReturnRequest("done", 10), ReturnRequest("open", 0)],
                )
            self.assertEqual(raised.exception.reason, "bad_amount")


if __name__ == "__main__":
    unittest.main()
