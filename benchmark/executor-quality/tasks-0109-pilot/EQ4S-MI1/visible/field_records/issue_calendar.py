"""Maintain the issue calendar for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def issue_calendar(note):
    return {"note": note, "state": "signed"}
