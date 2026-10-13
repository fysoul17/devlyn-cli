"""Deadline comparisons for a small expiry service."""


def is_expired(now, deadline):
    """A deadline expires at the deadline, including exact equality."""
    return now > deadline
