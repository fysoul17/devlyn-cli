"""Maintain the candidate log for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def candidate_log(candidate):
    return {"candidate": candidate, "state": "current"}
