"""Public examples for direct debit-writer behavior."""

import unittest

from quota.account_book import QuotaAccountBook
from quota.debit_journal import DebitJournal
from quota.debit_writer import DebitBatchWriter
from quota.errors import DebitWriteError
from quota.models import DebitOperation


class DebitWriterTests(unittest.TestCase):
    def test_successful_batch_updates_capacity_and_journal(self) -> None:
        accounts = QuotaAccountBook({"tenant-blue": 20})
        journal = DebitJournal()
        writer = DebitBatchWriter(accounts, journal)
        operations = [
            DebitOperation("job-a", "tenant-blue", "quota.consume", 4),
            DebitOperation("job-b", "tenant-blue", "quota.consume", 7),
        ]

        committed = writer.write_batch("tenant-blue", operations)

        self.assertEqual(["job-a", "job-b"], committed)
        self.assertEqual(9, accounts.remaining["tenant-blue"])
        self.assertEqual(2, len(journal.rows))

    def test_journal_failure_restores_direct_writer_state(self) -> None:
        accounts = QuotaAccountBook({"tenant-green": 15})
        journal = DebitJournal(fail_after_append={"job-stop"})
        writer = DebitBatchWriter(accounts, journal)
        operations = [
            DebitOperation("job-first", "tenant-green", "quota.consume", 3),
            DebitOperation("job-stop", "tenant-green", "quota.consume", 5),
        ]

        with self.assertRaises(DebitWriteError):
            writer.write_batch("tenant-green", operations)

        self.assertEqual({"tenant-green": 15}, accounts.remaining)
        self.assertEqual([], journal.rows)


if __name__ == "__main__":
    unittest.main()
