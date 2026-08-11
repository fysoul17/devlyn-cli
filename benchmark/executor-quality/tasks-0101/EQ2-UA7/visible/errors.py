"""Errors raised by inventory transfer batches."""

from __future__ import annotations

from models import DiscrepancyReport


class StockFault(RuntimeError):
    """The stock mover could not continue an operational write."""


class TransferRejected(RuntimeError):
    """A transfer batch was rejected with a ranked discrepancy report."""

    def __init__(self, report: DiscrepancyReport) -> None:
        if not report.ranked:
            raise ValueError("a rejected transfer needs a discrepancy")
        self.reason = report.ranked[0].reason
        self.report = report
        super().__init__(self.reason)
