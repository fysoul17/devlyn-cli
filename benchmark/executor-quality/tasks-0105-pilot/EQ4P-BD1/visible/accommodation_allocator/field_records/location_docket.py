"""Maintain the location docket for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def location_docket(candidate):
    return {"candidate": candidate, "state": "current"}
