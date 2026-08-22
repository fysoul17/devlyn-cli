"""Maintain the mint intake for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def mint_intake(note):
    return {"note": note, "state": "signed"}
