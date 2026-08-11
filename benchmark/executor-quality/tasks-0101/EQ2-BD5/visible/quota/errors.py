"""Failures exposed by quota accounting."""


class QuotaExceeded(Exception):
    """A tenant does not have enough remaining capacity."""


class DebitWriteError(Exception):
    """A debit journal append failed."""


class TenantScopeDenied(Exception):
    """An actor cannot perform an operation for the requested tenant."""
