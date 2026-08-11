"""Serialized state and endpoint writes for inventory transfers."""

from __future__ import annotations

from errors import StockFault
from models import Transfer
from state_codec import decode_state, encode_state


class StockStore:
    def __init__(
        self,
        stock: dict[str, dict[str, int]],
        capacities: dict[str, dict[str, int]],
        *,
        blocked: tuple[str, ...] = (),
    ) -> None:
        self._state: dict[str, object] = {
            "batches": [],
            "blocked": sorted(blocked),
            "capacities": {
                location: dict(slots) for location, slots in capacities.items()
            },
            "moves": [],
            "revision": 0,
            "stock": {location: dict(slots) for location, slots in stock.items()},
        }

    def snapshot_bytes(self) -> bytes:
        return encode_state(self._state)

    def restore_bytes(self, payload: bytes) -> None:
        self._state = decode_state(payload)

    def view(self) -> dict[str, object]:
        return decode_state(self.snapshot_bytes())

    def _stock(self) -> dict[str, object]:
        stock = self._state["stock"]
        assert isinstance(stock, dict)
        return stock

    def _slots(self, location: str) -> dict[str, object]:
        stock = self._stock()
        slots = stock.setdefault(location, {})
        assert isinstance(slots, dict)
        return slots

    def on_hand(self, location: str, sku: str) -> int:
        value = self._slots(location).get(sku, 0)
        assert isinstance(value, int)
        return value

    def destination_issue(self, transfer: Transfer) -> str | None:
        blocked = self._state["blocked"]
        capacities = self._state["capacities"]
        assert isinstance(blocked, list) and isinstance(capacities, dict)
        if transfer.destination in blocked:
            return "blocked"
        limits = capacities.get(transfer.destination, {})
        assert isinstance(limits, dict)
        limit = limits.get(transfer.sku)
        if isinstance(limit, int) and self.on_hand(transfer.destination, transfer.sku) + transfer.quantity > limit:
            return "full"
        return None

    def debit(self, transfer: Transfer) -> None:
        if transfer.fail_before_debit:
            raise StockFault("source transport failed")
        available = self.on_hand(transfer.source, transfer.sku)
        if available < transfer.quantity:
            raise StockFault("source stock changed")
        self._slots(transfer.source)[transfer.sku] = available - transfer.quantity
        self._bump_revision(1)

    def credit(self, transfer: Transfer) -> None:
        destination = self._slots(transfer.destination)
        destination[transfer.sku] = self.on_hand(transfer.destination, transfer.sku) + transfer.quantity
        moves = self._state["moves"]
        assert isinstance(moves, list)
        moves.append(
            {
                "destination": transfer.destination,
                "quantity": transfer.quantity,
                "sku": transfer.sku,
                "source": transfer.source,
            }
        )
        self._bump_revision(1)

    def undo(self, transfer: Transfer) -> None:
        moves = self._state["moves"]
        assert isinstance(moves, list)
        expected = {
            "destination": transfer.destination,
            "quantity": transfer.quantity,
            "sku": transfer.sku,
            "source": transfer.source,
        }
        if not moves or moves[-1] != expected:
            raise StockFault("completed move order changed")
        moves.pop()
        destination = self._slots(transfer.destination)
        destination[transfer.sku] = self.on_hand(transfer.destination, transfer.sku) - transfer.quantity
        source = self._slots(transfer.source)
        source[transfer.sku] = self.on_hand(transfer.source, transfer.sku) + transfer.quantity
        self._bump_revision(-2)

    def commit_batch(self, batch_id: str, *, fail: bool = False) -> None:
        if fail:
            raise StockFault("batch commit failed")
        batches = self._state["batches"]
        assert isinstance(batches, list)
        batches.append(batch_id)
        self._bump_revision(1)

    def _bump_revision(self, amount: int) -> None:
        revision = self._state["revision"]
        assert isinstance(revision, int)
        self._state["revision"] = revision + amount
