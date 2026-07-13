import os
import tempfile
import unittest

from vault.store import load_vault, notes_by_id, save_vault, titles


class StoreTest(unittest.TestCase):
    def test_committed_vault_loads(self):
        db = load_vault("data/notes.json")
        self.assertEqual(len(db["notes"]), 3)
        self.assertIn("schema_version", db)

    def test_notes_by_id(self):
        db = load_vault("data/notes.json")
        by_id = notes_by_id(db)
        self.assertEqual(sorted(by_id), ["n-1", "n-2", "n-3"])
        self.assertEqual(by_id["n-2"]["title"], "Vendor call")

    def test_titles_are_ordered_by_id(self):
        db = load_vault("data/notes.json")
        self.assertEqual(
            titles(db), ["Kickoff checklist", "Vendor call", "Retro notes"]
        )

    def test_save_then_load_round_trips(self):
        db = load_vault("data/notes.json")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "copy.json")
            save_vault(db, path)
            self.assertEqual(load_vault(path), db)


if __name__ == "__main__":
    unittest.main()
