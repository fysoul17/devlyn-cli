"""Maintain the checkin board for ordinary remote examinations.

The record keeps a current arrangement note without changing an allocation.
"""


def checkin_board(candidate):
    return {"candidate": candidate, "state": "current"}
