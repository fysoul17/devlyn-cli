import unittest

from sync import CatalogSync


class CatalogSyncTests(unittest.TestCase):
    def test_reports_current_state(self):
        catalog = CatalogSync([{"sku": "lamp"}], cursor=4)
        self.assertEqual(
            catalog.snapshot(),
            {
                "items": [{"sku": "lamp"}],
                "cursor": 4,
                "retry_count": 0,
                "quarantine_count": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
