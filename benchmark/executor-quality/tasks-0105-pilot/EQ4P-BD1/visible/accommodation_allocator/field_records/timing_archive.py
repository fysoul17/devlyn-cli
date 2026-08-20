"""Maintain the timing archive for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def timing_archive(candidate):
    return {"candidate": candidate, "state": "current"}
