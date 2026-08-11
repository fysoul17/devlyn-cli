"""Domain failures surfaced by the proration boundary."""


class EntitlementDenied(Exception):
    """The actor cannot move this subscription to the requested plan."""


class ChargeWriteError(Exception):
    """A charge record could not be committed."""


class EntitlementWriteError(Exception):
    """An entitlement window could not be committed."""
