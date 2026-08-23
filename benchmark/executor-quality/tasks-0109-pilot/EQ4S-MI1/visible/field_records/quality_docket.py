"""Maintain the quality docket for ordinary currency circulation.

The record marks a signed review without changing a note policy.
"""


def quality_docket(note):
    return {"note": note, "state": "signed"}
