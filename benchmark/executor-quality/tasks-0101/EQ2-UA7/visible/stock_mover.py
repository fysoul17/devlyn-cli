"""Coordinate endpoint writes and discrepancy reporting for one batch."""

from __future__ import annotations

from collections.abc import Sequence

from discrepancy_reporter import DiscrepancyReporter
from errors import TransferRejected
from models import BatchResult, Discrepancy, Transfer
from stock_store import StockStore


def _validation_issue(transfer: Transfer) -> str | None:
    if type(transfer.quantity) is not int or transfer.quantity <= 0:
        return "bad_qty"
    return None


def move_batch(
    store: StockStore,
    batch_id: str,
    transfers: Sequence[Transfer],
    *,
    reporter: DiscrepancyReporter | None = None,
    fail_on_commit: bool = False,
) -> BatchResult:
    """Move one batch and report any rejected transfer legs."""

    active_reporter = reporter if reporter is not None else DiscrepancyReporter()
    before = store.snapshot_bytes()
    completed: list[Transfer] = []
    discrepancies: list[Discrepancy] = []
    for source_index, transfer in enumerate(transfers):
        reason = _validation_issue(transfer)
        if reason is not None:
            discrepancies.append(
                Discrepancy(
                    source_index,
                    reason,
                    transfer.source,
                    transfer.destination,
                    transfer.sku,
                )
            )
            continue
        store.debit(transfer)
        reason = store.destination_issue(transfer)
        if reason is not None:
            discrepancies.append(
                Discrepancy(
                    source_index,
                    reason,
                    transfer.source,
                    transfer.destination,
                    transfer.sku,
                )
            )
            continue
        store.credit(transfer)
        completed.append(transfer)

    if discrepancies:
        report = active_reporter.build(discrepancies, before, store.snapshot_bytes())
        raise TransferRejected(report)
    store.commit_batch(batch_id, fail=fail_on_commit)
    return BatchResult(batch_id, tuple(completed))
