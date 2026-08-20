"""Maintain the materials record for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def materials_record(candidate):
    return {"candidate": candidate, "state": "current"}
