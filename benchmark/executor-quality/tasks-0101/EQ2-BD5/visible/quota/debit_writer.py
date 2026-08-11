"""Applies quota debit batches to capacity and journal state."""

from collections.abc import Iterable

from .account_book import QuotaAccountBook
from .debit_journal import DebitJournal
from .models import DebitOperation


class DebitBatchWriter:
    def __init__(self, accounts: QuotaAccountBook, journal: DebitJournal) -> None:
        self.accounts = accounts
        self.journal = journal

    def write_batch(
        self,
        tenant_id: str,
        operations: Iterable[DebitOperation],
    ) -> list[str]:
        """Apply one debit batch and return committed operation ids."""
        staged: list[DebitOperation] = []
        for operation in operations:
            self.accounts.debit(tenant_id, operation.units)
            staged.append(operation)
        for operation in staged:
            self.journal.append(tenant_id, operation)
        return [operation.operation_id for operation in staged]
