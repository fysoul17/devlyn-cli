"""Maintain the intake queue for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def intake_queue(candidate):
    return {"candidate": candidate, "state": "current"}
