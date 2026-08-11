"""Public examples for the dependent tenant-scope path."""

import unittest

from quota.account_book import QuotaAccountBook
from quota.debit_journal import DebitJournal
from quota.debit_writer import DebitBatchWriter
from quota.errors import TenantScopeDenied
from quota.models import DebitOperation
from quota.scope_check import TenantScopeCheck


class ScopeCheckTests(unittest.TestCase):
    def test_denied_first_operation_never_reaches_writer_state(self) -> None:
        accounts = QuotaAccountBook({"tenant-silver": 12})
        journal = DebitJournal()
        writer = DebitBatchWriter(accounts, journal)
        checker = TenantScopeCheck({"operator": {"tenant-silver": {"quota.read"}}})
        operations = [
            DebitOperation("job-denied", "tenant-silver", "quota.consume", 2),
            DebitOperation("job-later", "tenant-silver", "quota.read", 1),
        ]

        with self.assertRaises(TenantScopeDenied):
            checker.debit_batch(writer, "operator", "tenant-silver", operations)

        self.assertEqual({"tenant-silver": 12}, accounts.remaining)
        self.assertEqual([], journal.rows)


if __name__ == "__main__":
    unittest.main()
