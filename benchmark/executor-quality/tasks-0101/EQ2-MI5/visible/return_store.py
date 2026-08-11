"""File-backed order state used by the refund engine."""

from __future__ import annotations

from pathlib import Path

from errors import StoreFault
from models import ReturnRequest
from serialization import decode_store, encode_store


class ReturnStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def create(
        cls,
        path: Path,
        refundable_cents: dict[str, int],
        *,
        closed: tuple[str, ...] = (),
    ) -> "ReturnStore":
        closed_ids = set(closed)
        orders = {
            order_id: {
                "refundable_cents": amount,
                "refunded_cents": amount if order_id in closed_ids else 0,
            }
            for order_id, amount in refundable_cents.items()
        }
        value: dict[str, object] = {
            "completed_batches": [],
            "orders": orders,
            "refunds": [],
            "revision": 0,
        }
        path.write_bytes(encode_store(value))
        return cls(path)

    def snapshot_bytes(self) -> bytes:
        return self.path.read_bytes()

    def restore_bytes(self, payload: bytes) -> None:
        self.path.write_bytes(payload)

    def view(self) -> dict[str, object]:
        return decode_store(self.path.read_bytes())

    def rejection_reason(self, request: ReturnRequest) -> str | None:
        if request.amount_cents <= 0:
            return "bad_amount"
        orders = self.view()["orders"]
        assert isinstance(orders, dict)
        order = orders.get(request.order_id)
        if order is None:
            return "missing"
        assert isinstance(order, dict)
        refundable = order["refundable_cents"]
        refunded = order["refunded_cents"]
        assert isinstance(refundable, int) and isinstance(refunded, int)
        remaining = refundable - refunded
        if remaining == 0:
            return "closed"
        if request.amount_cents > remaining:
            return "bad_amount"
        return None

    def apply_refund(self, request: ReturnRequest) -> None:
        value = self.view()
        orders = value["orders"]
        refunds = value["refunds"]
        revision = value["revision"]
        assert isinstance(orders, dict) and isinstance(refunds, list)
        assert isinstance(revision, int)
        order = orders[request.order_id]
        assert isinstance(order, dict)
        refunded = order["refunded_cents"]
        assert isinstance(refunded, int)
        order["refunded_cents"] = refunded + request.amount_cents
        refunds.append({"amount_cents": request.amount_cents, "order_id": request.order_id})
        value["revision"] = revision + 1
        self.path.write_bytes(encode_store(value))
        if request.fail_after_write:
            raise StoreFault("refund write failed")

    def finalize_batch(self, batch_id: str, *, fail: bool = False) -> None:
        value = self.view()
        completed = value["completed_batches"]
        revision = value["revision"]
        assert isinstance(completed, list) and isinstance(revision, int)
        completed.append(batch_id)
        value["revision"] = revision + 1
        self.path.write_bytes(encode_store(value))
        if fail:
            raise StoreFault("batch finalization failed")
