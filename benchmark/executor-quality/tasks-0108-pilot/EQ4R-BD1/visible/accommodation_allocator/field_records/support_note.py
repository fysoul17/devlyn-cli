"""Maintain the support note for ordinary remote examinations.

The record keeps a current accommodation note for expiry review and assigns no
remote staff member without changing an allocation.
"""


def support_note(candidate):
    return {"candidate": candidate, "state": "current"}
