import unittest

from manifest_dedup import ManifestDedup


class ManifestDedupTests(unittest.TestCase):
    def test_existing_manifest_is_not_scheduled(self) -> None:
        registry = ManifestDedup(["old"])
        scheduled = registry.absorb(
            [{"id": "old", "asset": "clip", "priority": 2, "duplicate": False}]
        )
        self.assertEqual(scheduled, [])
        self.assertEqual(registry.manifest_ids(), ["old"])


if __name__ == "__main__":
    unittest.main()
