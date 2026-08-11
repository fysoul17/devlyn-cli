"""Quota debit request records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DebitOperation:
    operation_id: str
    tenant_id: str
    scope: str
    units: int
