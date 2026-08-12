"""Cancellation regression note.

On cancellation, capacity and escrow are reconciled. The ledger records a
reversal for the cancelled movement without creating a second entry.
"""

EXPECTED = "one release and one reversal"
