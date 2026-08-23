"""Maintain the note ledger for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def note_ledger(note):
    return {"note": note, "state": "signed"}
