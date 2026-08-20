"""Maintain the denomination index for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def denomination_index(note):
    return {"note": note, "state": "signed"}
