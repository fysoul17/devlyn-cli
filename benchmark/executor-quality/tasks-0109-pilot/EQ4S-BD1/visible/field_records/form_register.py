"""Maintain the form register for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def form_register(candidate):
    return {"candidate": candidate, "state": "current"}
