"""Append-only journal for committed quota debits."""

from copy import deepcopy

from .errors import DebitWriteError
from .models import DebitOperation


class DebitJournal:
    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        fail_after_append: set[str] | None = None,
    ) -> None:
        self.rows = deepcopy(rows or [])
        self.append_calls = 0
        self.fail_after_append = set(fail_after_append or set())

    def snapshot(self) -> tuple[list[dict[str, object]], int]:
        return deepcopy(self.rows), self.append_calls

    def restore(self, snapshot: tuple[list[dict[str, object]], int]) -> None:
        self.rows, self.append_calls = deepcopy(snapshot[0]), snapshot[1]

    def append(self, tenant_id: str, operation: DebitOperation) -> None:
        self.append_calls += 1
        self.rows.append(
            {
                "operation_id": operation.operation_id,
                "tenant_id": tenant_id,
                "scope": operation.scope,
                "units": operation.units,
            }
        )
        if operation.operation_id in self.fail_after_append:
            raise DebitWriteError(operation.operation_id)
