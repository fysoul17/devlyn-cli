import unittest

from vault.migrate import apply_migrations
from vault.schema import SCHEMA_VERSION


def sample_vault(schema_version):
    return {
        "schema_version": schema_version,
        "notes": [
            {
                "id": "x-1",
                "title": "Sample",
                "body": "one two three",
                "created": "2024-01-01",
            }
        ],
    }


class MigrateTest(unittest.TestCase):
    def test_vault_at_current_version_has_nothing_pending(self):
        db = sample_vault(SCHEMA_VERSION)
        self.assertEqual(apply_migrations(db), [])
        self.assertEqual(db["schema_version"], SCHEMA_VERSION)

    def test_migrating_is_idempotent(self):
        db = sample_vault(1)
        apply_migrations(db)
        after_first = dict(db)
        self.assertEqual(apply_migrations(db), [])
        self.assertEqual(db, after_first)

    def test_migration_reaches_the_expected_version(self):
        db = sample_vault(1)
        apply_migrations(db)
        self.assertEqual(db["schema_version"], SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
