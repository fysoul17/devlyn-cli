"""Mutable remaining-capacity state for tenants."""

from copy import deepcopy

from .errors import QuotaExceeded


class QuotaAccountBook:
    def __init__(self, remaining: dict[str, int]) -> None:
        self.remaining = deepcopy(remaining)
        self.debit_calls = 0

    def snapshot(self) -> tuple[dict[str, int], int]:
        return deepcopy(self.remaining), self.debit_calls

    def restore(self, snapshot: tuple[dict[str, int], int]) -> None:
        self.remaining, self.debit_calls = deepcopy(snapshot[0]), snapshot[1]

    def debit(self, tenant_id: str, units: int) -> None:
        available = self.remaining[tenant_id]
        if units > available:
            raise QuotaExceeded(tenant_id)
        self.remaining[tenant_id] = available - units
        self.debit_calls += 1
