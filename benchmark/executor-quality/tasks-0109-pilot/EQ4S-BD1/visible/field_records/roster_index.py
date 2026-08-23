"""Maintain the roster index for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def roster_index(candidate):
    return {"candidate": candidate, "state": "current"}
