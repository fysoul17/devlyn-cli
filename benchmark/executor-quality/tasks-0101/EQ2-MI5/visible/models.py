"""Public values used by the refund engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReturnRequest:
    order_id: str
    amount_cents: int
    fail_after_write: bool = False


@dataclass(frozen=True)
class Rejection:
    source_index: int
    reason: str


@dataclass(frozen=True)
class BatchResult:
    batch_id: str
    refunded_order_ids: tuple[str, ...]
