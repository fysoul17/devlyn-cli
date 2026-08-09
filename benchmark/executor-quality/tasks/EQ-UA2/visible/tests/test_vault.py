import unittest

from vault import has_scope, list_artifacts, lookup_artifact


class VaultTests(unittest.TestCase):
    def test_lists_artifacts_stably(self) -> None:
        self.assertEqual(list_artifacts({"z": {}, "a": {}}), ["a", "z"])

    def test_checks_scopes_and_catalog_entries(self) -> None:
        grants = {"reader": ["read"]}
        catalog = {"bundle.zip": {"bytes": 4}}

        self.assertTrue(has_scope(grants, "reader", "read"))
        self.assertFalse(has_scope(grants, "reader", "write"))
        self.assertEqual(lookup_artifact(catalog, "bundle.zip"), {"bytes": 4})


if __name__ == "__main__":
    unittest.main()
