import unittest

from catalog import SnapshotCatalog
from models import CatalogEntry, RotationPlan, SnapshotDraft
from rotation import apply_rotation
from snapshot_store import SnapshotStore


class RotationTests(unittest.TestCase):
    def test_successful_rotation_advances_chain(self):
        store = SnapshotStore(2, [(0, "old", b"old")], next_slot=1)
        catalog = SnapshotCatalog([CatalogEntry("old", 0, None)])
        result = apply_rotation(
            store,
            catalog,
            RotationPlan("nightly", 2, [SnapshotDraft("new", b"new")]),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.applied, ("new",))
        self.assertEqual(
            catalog.view()[0],
            (CatalogEntry("old", 0, None), CatalogEntry("new", 1, "old")),
        )

    def test_write_failure_is_reported(self):
        store = SnapshotStore(2)
        catalog = SnapshotCatalog()
        result = apply_rotation(
            store,
            catalog,
            RotationPlan("broken", 2, [SnapshotDraft("new", b"x", True)]),
        )
        self.assertFalse(result.ok)
        self.assertIn("write failed", result.error)

    def test_store_allocation_can_be_rewound(self):
        store = SnapshotStore(3, next_slot=2)
        mark = store.allocation_mark()
        self.assertEqual(store.reserve(), 2)
        store.rewind_allocation(mark)
        self.assertEqual(store.reserve(), 2)

    def test_catalog_checks_physical_ownership(self):
        store = SnapshotStore(2, [(1, "snap", b"payload")])
        catalog = SnapshotCatalog([CatalogEntry("snap", 1, None)])
        self.assertTrue(catalog.agrees_with(store))


if __name__ == "__main__":
    unittest.main()
