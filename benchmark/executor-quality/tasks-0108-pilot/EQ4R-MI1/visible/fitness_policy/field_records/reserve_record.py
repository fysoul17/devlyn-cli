"""Maintain the reserve record for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def reserve_record(note):
    return {"note": note, "state": "signed"}
