"""Business ordering and endpoint drift for rejected transfers."""

from __future__ import annotations

from collections.abc import Iterable

from models import Discrepancy, DiscrepancyReport
from state_codec import decode_state


REASON_PRIORITY = {
    "bad_qty": 0,
    "blocked": 1,
    "full": 2,
}


class DiscrepancyReporter:
    def rank(self, discrepancies: Iterable[Discrepancy]) -> tuple[Discrepancy, ...]:
        return tuple(
            sorted(
                discrepancies,
                key=lambda item: (REASON_PRIORITY[item.reason], item.source_index),
            )
        )

    def build(
        self,
        discrepancies: Iterable[Discrepancy],
        before: bytes,
        after: bytes,
    ) -> DiscrepancyReport:
        return DiscrepancyReport(self.rank(discrepancies), self._drift(before, after))

    def _drift(self, before: bytes, after: bytes) -> tuple[tuple[str, str, int], ...]:
        before_stock = self._stock(decode_state(before))
        after_stock = self._stock(decode_state(after))
        rows: list[tuple[str, str, int]] = []
        for location in sorted(set(before_stock) | set(after_stock)):
            before_slots = self._slots(before_stock, location)
            after_slots = self._slots(after_stock, location)
            for sku in sorted(set(before_slots) | set(after_slots)):
                delta = self._quantity(after_slots, sku) - self._quantity(before_slots, sku)
                if delta:
                    rows.append((location, sku, delta))
        return tuple(rows)

    @staticmethod
    def _stock(state: dict[str, object]) -> dict[str, object]:
        stock = state["stock"]
        assert isinstance(stock, dict)
        return stock

    @staticmethod
    def _slots(stock: dict[str, object], location: str) -> dict[str, object]:
        value = stock.get(location, {})
        assert isinstance(value, dict)
        return value

    @staticmethod
    def _quantity(slots: dict[str, object], sku: str) -> int:
        value = slots.get(sku, 0)
        assert isinstance(value, int)
        return value
