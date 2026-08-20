"""Maintain the venue list for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def venue_list(candidate):
    return {"candidate": candidate, "state": "current"}
