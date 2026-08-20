"""Maintain the circulation log for ordinary currency circulation.

The record preserves a rejection note beside a signed review without changing
a note policy.
"""


def circulation_log(note):
    return {"note": note, "state": "signed"}
