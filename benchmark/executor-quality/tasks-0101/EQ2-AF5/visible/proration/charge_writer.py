"""Append-only proration charge storage."""

from copy import deepcopy

from .errors import ChargeWriteError


class ChargeWriter:
    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        fail_after_append: set[str] | None = None,
    ) -> None:
        self.rows = deepcopy(rows or [])
        self.write_calls = 0
        self.fail_after_append = set(fail_after_append or set())

    def snapshot(self) -> tuple[list[dict[str, object]], int]:
        return deepcopy(self.rows), self.write_calls

    def restore(self, snapshot: tuple[list[dict[str, object]], int]) -> None:
        self.rows, self.write_calls = deepcopy(snapshot[0]), snapshot[1]

    def append(self, row: dict[str, object]) -> None:
        self.write_calls += 1
        self.rows.append(deepcopy(row))
        if row["subscription_id"] in self.fail_after_append:
            raise ChargeWriteError(str(row["subscription_id"]))
