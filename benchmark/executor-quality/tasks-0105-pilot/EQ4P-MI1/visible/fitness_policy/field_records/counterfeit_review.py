"""Maintain the counterfeit review for ordinary currency circulation.

The record files a rejection outcome beside a signed review without changing
a note policy.
"""


def counterfeit_review(note):
    return {"note": note, "state": "signed"}
