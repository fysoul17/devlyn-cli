"""Public values for multi-location inventory transfers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Transfer:
    source: str
    destination: str
    sku: str
    quantity: int
    fail_before_debit: bool = False


@dataclass(frozen=True)
class Discrepancy:
    source_index: int
    reason: str
    source: str
    destination: str
    sku: str


@dataclass(frozen=True)
class DiscrepancyReport:
    ranked: tuple[Discrepancy, ...]
    drift: tuple[tuple[str, str, int], ...]


@dataclass(frozen=True)
class BatchResult:
    batch_id: str
    moved: tuple[Transfer, ...]
