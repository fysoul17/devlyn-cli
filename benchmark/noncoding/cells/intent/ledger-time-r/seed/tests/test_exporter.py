from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.exporter import export_row


class ExportRowTests(unittest.TestCase):
    def test_row_shape(self) -> None:
        row = export_row("north-pier", datetime(2025, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(set(row), {"account", "last_seen"})
        self.assertEqual(row["account"], "north-pier")


if __name__ == "__main__":
    unittest.main()
