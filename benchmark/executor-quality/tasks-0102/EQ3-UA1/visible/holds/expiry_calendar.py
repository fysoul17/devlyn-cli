"""Determine whether a pickup window has elapsed."""


def elapsed(last_day, today, limit=5):
    return today - last_day >= limit
