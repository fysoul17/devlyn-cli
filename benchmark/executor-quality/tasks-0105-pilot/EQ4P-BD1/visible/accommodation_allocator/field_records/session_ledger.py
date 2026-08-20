"""Maintain the session ledger for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def session_ledger(candidate):
    return {"candidate": candidate, "state": "current"}
