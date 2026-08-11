"""Errors raised by the order-return service."""

from __future__ import annotations

from collections.abc import Sequence

from models import Rejection


class StoreFault(RuntimeError):
    """The durable store failed after attempting a write."""


class RefundBatchError(RuntimeError):
    """A return batch was rejected with ranked failure details."""

    def __init__(self, rejections: Sequence[Rejection]) -> None:
        ordered = tuple(rejections)
        if not ordered:
            raise ValueError("a rejected batch needs at least one cause")
        self.reason = ordered[0].reason
        self.rejections = ordered
        super().__init__(self.reason)
