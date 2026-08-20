"""Maintain the tender queue for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def tender_queue(note):
    return {"note": note, "state": "signed"}
