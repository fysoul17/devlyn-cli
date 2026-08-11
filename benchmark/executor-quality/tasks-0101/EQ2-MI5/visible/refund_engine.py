"""Coordinate refund writes and rejection reporting."""

from __future__ import annotations

from collections.abc import Sequence

from errors import RefundBatchError
from models import BatchResult, Rejection, ReturnRequest
from return_store import ReturnStore


def process_returns(
    store: ReturnStore,
    batch_id: str,
    requests: Sequence[ReturnRequest],
    *,
    fail_on_commit: bool = False,
) -> BatchResult:
    """Apply one batch and report any rejected requests."""

    refunded: list[str] = []
    rejections: list[Rejection] = []
    for source_index, request in enumerate(requests):
        reason = store.rejection_reason(request)
        if reason is not None:
            rejections.append(Rejection(source_index, reason))
            continue
        store.apply_refund(request)
        refunded.append(request.order_id)

    store.finalize_batch(batch_id, fail=fail_on_commit)
    if rejections:
        raise RefundBatchError(rejections)
    return BatchResult(batch_id, tuple(refunded))
