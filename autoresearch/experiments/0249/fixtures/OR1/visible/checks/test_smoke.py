from pathlib import Path
import tempfile
import unittest
from folio import FileStore, StorageError, TransactionClosed, Workspace

class Smoke(unittest.TestCase):
    def test_save_reopen_and_delete(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "articles.json"
            workspace = Workspace(FileStore(path))
            transaction = workspace.begin()
            transaction.put("welcome", {"text": "Hello"})
            self.assertEqual(transaction.get("welcome"), {"text": "Hello"})
            self.assertEqual(transaction.commit().revision, 1)
            reopened = Workspace(FileStore(path))
            self.assertEqual(reopened.snapshot().documents, {"welcome": {"text": "Hello"}})
            delete = reopened.begin()
            delete.delete("welcome")
            self.assertEqual(delete.commit().documents, {})

    def test_rollback_closes_and_malformed_is_visible(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "articles.json"
            workspace = Workspace(FileStore(path))
            transaction = workspace.begin()
            transaction.put("draft", {"text": "discard"})
            transaction.rollback()
            self.assertEqual(workspace.snapshot().documents, {})
            with self.assertRaises(TransactionClosed):
                transaction.commit()
            path.write_text("broken")
            with self.assertRaises(StorageError):
                workspace.refresh()
