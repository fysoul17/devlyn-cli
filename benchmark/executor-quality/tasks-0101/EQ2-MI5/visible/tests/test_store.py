from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from models import ReturnRequest
from return_store import ReturnStore


class ReturnStoreTests(unittest.TestCase):
    def test_store_encoding_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = ReturnStore.create(Path(root) / "orders.json", {"b": 200, "a": 100})
            original = store.snapshot_bytes()
            store.restore_bytes(original)
            self.assertEqual(store.snapshot_bytes(), original)

    def test_refund_updates_order_and_journal(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = ReturnStore.create(Path(root) / "orders.json", {"open": 400})
            store.apply_refund(ReturnRequest("open", 125))
            view = store.view()
            self.assertEqual(view["orders"]["open"]["refunded_cents"], 125)
            self.assertEqual(view["refunds"], [{"amount_cents": 125, "order_id": "open"}])


if __name__ == "__main__":
    unittest.main()
